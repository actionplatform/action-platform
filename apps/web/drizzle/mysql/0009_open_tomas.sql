CREATE TABLE `template_source` (
	`id` varchar(36) NOT NULL,
	`organization_id` varchar(36) NOT NULL,
	`name` varchar(64) NOT NULL,
	`url` text NOT NULL,
	`ref` varchar(128) NOT NULL DEFAULT 'v1',
	`source_host_id` varchar(36),
	`created_at` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `template_source_id` PRIMARY KEY(`id`)
);
ALTER TABLE `template_source` ADD CONSTRAINT `template_source_organization_id_organization_id_fk` FOREIGN KEY (`organization_id`) REFERENCES `organization`(`id`) ON DELETE cascade ON UPDATE no action;