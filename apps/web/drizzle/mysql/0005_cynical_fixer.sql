CREATE TABLE `release` (
	`id` varchar(36) NOT NULL,
	`app_id` varchar(36) NOT NULL,
	`tag` varchar(255) NOT NULL,
	`name` text,
	`body` text,
	`url` text,
	`author` text,
	`sha` varchar(64),
	`prerelease` boolean NOT NULL DEFAULT false,
	`draft` boolean NOT NULL DEFAULT false,
	`published_at` timestamp,
	`source` varchar(16) NOT NULL,
	`synced_at` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `release_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
ALTER TABLE `release` ADD CONSTRAINT `release_app_id_app_id_fk` FOREIGN KEY (`app_id`) REFERENCES `app`(`id`) ON DELETE cascade ON UPDATE no action;