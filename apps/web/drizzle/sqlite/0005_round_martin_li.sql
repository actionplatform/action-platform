CREATE TABLE `release` (
	`id` text PRIMARY KEY NOT NULL,
	`app_id` text NOT NULL,
	`tag` text NOT NULL,
	`name` text,
	`body` text,
	`url` text,
	`author` text,
	`sha` text,
	`prerelease` integer DEFAULT false NOT NULL,
	`draft` integer DEFAULT false NOT NULL,
	`published_at` integer,
	`source` text NOT NULL,
	`synced_at` integer NOT NULL,
	FOREIGN KEY (`app_id`) REFERENCES `app`(`id`) ON UPDATE no action ON DELETE cascade
);
