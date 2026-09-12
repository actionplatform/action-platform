ALTER TABLE "source_host" ADD COLUMN "auth_kind" text DEFAULT 'token' NOT NULL;--> statement-breakpoint
ALTER TABLE "source_host" ADD COLUMN "login" text;--> statement-breakpoint
ALTER TABLE "source_host" ADD COLUMN "refresh_token_encrypted" text;--> statement-breakpoint
ALTER TABLE "source_host" ADD COLUMN "expires_at" timestamp;