"""Global search across matters, entities, emails, and documents."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.communications import DocumentRecord, EmailRecord
from app.models.entity import Entity
from app.models.matter import Matter
from app.services.matter import MatterService


class SearchService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search(self, *, user: User, q: str, limit: int = 20) -> dict:
        term = (q or "").strip()
        if len(term) < 2:
            return {"query": term, "matters": [], "entities": [], "emails": [], "documents": []}

        like = f"%{term}%"
        matter_acl = MatterService(self.db)._visible_filter(user)

        # Prefer Postgres full-text when available; fall back to ILIKE + trigram-friendly patterns
        matter_text = or_(
            Matter.name.ilike(like),
            Matter.matter_number.ilike(like),
            Matter.claim_number.ilike(like),
            Matter.policy_number.ilike(like),
            Matter.case_number.ilike(like),
            Matter.property_address.ilike(like),
            Matter.notes.ilike(like),
            Matter.search_keywords.ilike(like),
            func.coalesce(Matter.ai_summary, "").ilike(like),
        )
        try:
            fts = func.to_tsvector(
                "english",
                func.concat_ws(
                    " ",
                    Matter.name,
                    Matter.matter_number,
                    Matter.claim_number,
                    Matter.policy_number,
                    Matter.case_number,
                    Matter.property_address,
                    Matter.notes,
                    Matter.search_keywords,
                ),
            ).op("@@")(func.plainto_tsquery("english", term))
            matter_text = or_(matter_text, fts)
        except Exception:  # noqa: BLE001
            pass

        matters = self.db.scalars(
            select(Matter)
            .where(Matter.is_deleted.is_(False), matter_acl, matter_text)
            .limit(limit)
        ).all()

        entities = self.db.scalars(
            select(Entity)
            .where(
                Entity.is_deleted.is_(False),
                or_(
                    Entity.display_name.ilike(like),
                    Entity.legal_name.ilike(like),
                    Entity.primary_email.ilike(like),
                    Entity.primary_domain.ilike(like),
                    Entity.notes.ilike(like),
                ),
            )
            .limit(limit)
        ).all()

        # Emails/docs: hide rows linked to restricted matters the user cannot see
        email_matter_ok = or_(
            EmailRecord.primary_matter_id.is_(None),
            EmailRecord.primary_matter_id.in_(
                select(Matter.id).where(Matter.is_deleted.is_(False), matter_acl)
            ),
        )
        emails = self.db.scalars(
            select(EmailRecord)
            .where(
                EmailRecord.is_deleted.is_(False),
                email_matter_ok,
                or_(
                    EmailRecord.subject.ilike(like),
                    EmailRecord.sender.ilike(like),
                    EmailRecord.snippet.ilike(like),
                    EmailRecord.body_text.ilike(like),
                ),
            )
            .limit(limit)
        ).all()

        doc_matter_ok = or_(
            DocumentRecord.primary_matter_id.is_(None),
            DocumentRecord.primary_matter_id.in_(
                select(Matter.id).where(Matter.is_deleted.is_(False), matter_acl)
            ),
        )
        documents = self.db.scalars(
            select(DocumentRecord)
            .where(
                DocumentRecord.is_deleted.is_(False),
                doc_matter_ok,
                or_(
                    DocumentRecord.file_name.ilike(like),
                    DocumentRecord.current_path.ilike(like),
                    DocumentRecord.extracted_text.ilike(like),
                ),
            )
            .limit(limit)
        ).all()

        return {
            "query": term,
            "matters": [
                {
                    "id": str(m.id),
                    "matter_number": m.matter_number,
                    "name": m.name,
                    "claim_number": m.claim_number,
                    "href": f"/matters/{m.id}",
                }
                for m in matters
            ],
            "entities": [
                {
                    "id": str(e.id),
                    "display_name": e.display_name,
                    "email": e.primary_email,
                    "href": f"/entities/{e.id}",
                }
                for e in entities
            ],
            "emails": [
                {
                    "id": str(e.id),
                    "subject": e.subject,
                    "sender": e.sender,
                    "matter_name": e.primary_matter.name if e.primary_matter else None,
                    "href": e.gmail_message_link or "/emails",
                }
                for e in emails
            ],
            "documents": [
                {
                    "id": str(d.id),
                    "file_name": d.file_name,
                    "source_system": d.source_system,
                    "matter_name": d.primary_matter.name if d.primary_matter else None,
                    "href": d.direct_link or "/documents",
                }
                for d in documents
            ],
        }
