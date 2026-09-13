CREATE TABLE `api_token` (
	`id` varchar(36) NOT NULL,
	`user_id` varchar(36) NOT NULL,
	`organization_id` varchar(36) NOT NULL,
	`name` varchar(255) NOT NULL,
	`scope` varchar(255) NOT NULL,
	`created_at` timestamp NOT NULL DEFAULT (now()),
	`expires_at` timestamp NOT NULL,
	`last_used_at` timestamp,
	`revoked_at` timestamp,
	CONSTRAINT `api_token_id` PRIMARY KEY(`id`)
);
ALTER TABLE `api_token` ADD CONSTRAINT `api_token_user_id_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `api_token` ADD CONSTRAINT `api_token_organization_id_organization_id_fk` FOREIGN KEY (`organization_id`) REFERENCES `organization`(`id`) ON DELETE cascade ON UPDATE no action;