CREATE TABLE `pull_request` (
	`id` varchar(36) NOT NULL,
	`app_id` varchar(36) NOT NULL,
	`number` int NOT NULL,
	`title` text NOT NULL,
	`url` text NOT NULL,
	`author` text,
	`head` text NOT NULL,
	`base` text NOT NULL,
	`state` varchar(16) NOT NULL,
	`draft` boolean NOT NULL DEFAULT false,
	`created_at` timestamp NOT NULL,
	`updated_at` timestamp NOT NULL,
	`merged_at` timestamp,
	`source` varchar(32) NOT NULL,
	`synced_at` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `pull_request_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
ALTER TABLE `pull_request` ADD CONSTRAINT `pull_request_app_id_app_id_fk` FOREIGN KEY (`app_id`) REFERENCES `app`(`id`) ON DELETE cascade ON UPDATE no action;