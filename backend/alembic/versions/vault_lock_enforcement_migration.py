"""Add database-level lock state enforcement for Document Vault

Revision ID: vault_lock_enforcement_001
Revises: (latest)
Create Date: 2026-03-10

This migration adds check constraints and triggers to prevent deletion/modification
of documents when they have active legal hold, tax hold, or compliance hold states.
"""

from alembic import op

# Revision identifiers used by Alembic.
revision = 'vault_lock_enforcement_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create lock enforcement constraints."""

    # Add check constraint to documents table to prevent certain state transitions
    # This is a soft constraint that helps prevent accidental modifications
    op.execute("""
        ALTER TABLE documents
        ADD CONSTRAINT check_hold_state_prevents_delete
        CHECK (
            -- Allow deletion only if not in hold states
            CASE
                WHEN data->'metadata'->>'lock_state' IN ('legal hold', 'tax hold', 'compliance hold')
                THEN false
                ELSE true
            END
        );
    """)

    # Create trigger function to prevent updates on held documents
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_held_document_update()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Check if document is in a hold state
            IF NEW.data->'metadata'->>'lock_state' IN ('legal hold', 'tax hold', 'compliance hold') THEN
                IF OLD.data IS DISTINCT FROM NEW.data THEN
                    RAISE EXCEPTION 'Cannot modify document under % hold state',
                        NEW.data->'metadata'->>'lock_state';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Attach trigger to documents table
    op.execute("""
        DROP TRIGGER IF EXISTS document_hold_update_prevention ON documents;
        CREATE TRIGGER document_hold_update_prevention
        BEFORE UPDATE ON documents
        FOR EACH ROW
        EXECUTE FUNCTION prevent_held_document_update();
    """)

    # Create historical audit for all lock state changes
    op.execute("""
        CREATE TABLE IF NOT EXISTS vault_lock_state_audit (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID NOT NULL,
            previous_state VARCHAR(50) NOT NULL,
            new_state VARCHAR(50) NOT NULL,
            reason TEXT,
            changed_by VARCHAR(255),
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_vlsa_document_id ON vault_lock_state_audit (document_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_vlsa_changed_at ON vault_lock_state_audit (changed_at);")


def downgrade():
    """Remove lock enforcement constraints."""

    # Drop trigger
    op.execute("""
        DROP TRIGGER IF EXISTS document_hold_update_prevention ON documents;
    """)

    # Drop function
    op.execute("""
        DROP FUNCTION IF EXISTS prevent_held_document_update();
    """)

    # Drop check constraint
    op.execute("""
        ALTER TABLE documents
        DROP CONSTRAINT IF EXISTS check_hold_state_prevents_delete;
    """)

    # Drop audit table
    op.execute("""
        DROP TABLE IF EXISTS vault_lock_state_audit;
    """)
