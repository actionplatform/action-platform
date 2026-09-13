CREATE TABLE "organization_setting" (
	"organization_id" text PRIMARY KEY NOT NULL,
	"git_author_name" text NOT NULL,
	"git_author_email" text NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "organization_setting" ADD CONSTRAINT "organization_setting_organization_id_organization_id_fk" FOREIGN KEY ("organization_id") REFERENCES "public"."organization"("id") ON DELETE cascade ON UPDATE no action;