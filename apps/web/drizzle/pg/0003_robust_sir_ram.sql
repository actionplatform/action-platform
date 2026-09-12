CREATE TABLE "source_host" (
	"id" text PRIMARY KEY NOT NULL,
	"organization_id" text NOT NULL,
	"kind" text NOT NULL,
	"name" text NOT NULL,
	"base_url" text,
	"username" text,
	"token_encrypted" text NOT NULL,
	"default_owner" text,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "app" ADD COLUMN "source_host_id" text;--> statement-breakpoint
ALTER TABLE "source_host" ADD CONSTRAINT "source_host_organization_id_organization_id_fk" FOREIGN KEY ("organization_id") REFERENCES "public"."organization"("id") ON DELETE cascade ON UPDATE no action;