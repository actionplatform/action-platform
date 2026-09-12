CREATE TABLE `source_host` (
	`id` varchar(36) NOT NULL,
	`organization_id` varchar(36) NOT NULL,
	`kind` varchar(16) NOT NULL,
	`name` text NOT NULL,
	`base_url` text,
	`username` text,
	`token_encrypted` text NOT NULL,
	`default_owner` text,
	`created_at` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `source_host_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
ALTER TABLE `app` ADD `source_host_id` varchar(36);--> statement-breakpoint
ALTER TABLE `source_host` ADD CONSTRAINT `source_host_organization_id_organization_id_fk` FOREIGN KEY (`organization_id`) REFERENCES `organization`(`id`) ON DELETE cascade ON UPDATE no action;