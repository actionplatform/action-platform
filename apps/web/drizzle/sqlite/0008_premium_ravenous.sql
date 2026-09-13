CREATE TABLE `pull_request` (
	`id` text PRIMARY KEY NOT NULL,
	`app_id` text NOT NULL,
	`number` integer NOT NULL,
	`title` text NOT NULL,
	`url` text NOT NULL,
	`author` text,
	`head` text NOT NULL,
	`base` text NOT NULL,
	`state` text NOT NULL,
	`draft` integer DEFAULT false NOT NULL,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL,
	`merged_at` integer,
	`source` text NOT NULL,
	`synced_at` integer NOT NULL,
	FOREIGN KEY (`app_id`) REFERENCES `app`(`id`) ON UPDATE no action ON DELETE cascade
);
