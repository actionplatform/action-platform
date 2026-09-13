CREATE TABLE "release" (
	"id" text PRIMARY KEY NOT NULL,
	"app_id" text NOT NULL,
	"tag" text NOT NULL,
	"name" text,
	"body" text,
	"url" text,
	"author" text,
	"sha" text,
	"prerelease" boolean DEFAULT false NOT NULL,
	"draft" boolean DEFAULT false NOT NULL,
	"published_at" timestamp,
	"source" text NOT NULL,
	"synced_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "release" ADD CONSTRAINT "release_app_id_app_id_fk" FOREIGN KEY ("app_id") REFERENCES "public"."app"("id") ON DELETE cascade ON UPDATE no action;