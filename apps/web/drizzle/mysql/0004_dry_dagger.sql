ALTER TABLE `source_host` ADD `auth_kind` varchar(16) DEFAULT 'token' NOT NULL;--> statement-breakpoint
ALTER TABLE `source_host` ADD `login` text;--> statement-breakpoint
ALTER TABLE `source_host` ADD `refresh_token_encrypted` text;--> statement-breakpoint
ALTER TABLE `source_host` ADD `expires_at` timestamp;