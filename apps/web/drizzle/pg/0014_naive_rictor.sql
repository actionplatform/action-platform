CREATE TABLE "api_token_client" (
	"id" text PRIMARY KEY NOT NULL,
	"token_id" text NOT NULL,
	"name" text NOT NULL,
	"first_seen_at" timestamp DEFAULT now() NOT NULL,
	"last_seen_at" timestamp DEFAULT now() NOT NULL
);
ALTER TABLE "api_token_client" ADD CONSTRAINT "api_token_client_token_id_api_token_id_fk" FOREIGN KEY ("token_id") REFERENCES "public"."api_token"("id") ON DELETE cascade ON UPDATE no action;