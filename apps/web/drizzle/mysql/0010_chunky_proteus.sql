CREATE TABLE `organization_setting` (
	`organization_id` varchar(36) NOT NULL,
	`git_author_name` varchar(255) NOT NULL,
	`git_author_email` varchar(255) NOT NULL,
	`updated_at` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `organization_setting_organization_id` PRIMARY KEY(`organization_id`)
);
--> statement-breakpoint
ALTER TABLE `organization_setting` ADD CONSTRAINT `organization_setting_organization_id_organization_id_fk` FOREIGN KEY (`organization_id`) REFERENCES `organization`(`id`) ON DELETE cascade ON UPDATE no action;