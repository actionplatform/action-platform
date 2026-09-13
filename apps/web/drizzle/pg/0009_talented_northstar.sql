CREATE TABLE "template_source" (
	"id" text PRIMARY KEY NOT NULL,
	"organization_id" text NOT NULL,
	"name" text NOT NULL,
	"url" text NOT NULL,
	"ref" text DEFAULT 'v1' NOT NULL,
	"source_host_id" text,
	"created_at" timestamp DEFAULT now() NOT NULL
);
ALTER TABLE "template_source" ADD CONSTRAINT "template_source_organization_id_organization_id_fk" FOREIGN KEY ("organization_id") REFERENCES "public"."organization"("id") ON DELETE cascade ON UPDATE no action;