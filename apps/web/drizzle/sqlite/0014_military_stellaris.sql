CREATE TABLE `api_token_client` (
	`id` text PRIMARY KEY NOT NULL,
	`token_id` text NOT NULL,
	`name` text NOT NULL,
	`first_seen_at` integer NOT NULL,
	`last_seen_at` integer NOT NULL,
	FOREIGN KEY (`token_id`) REFERENCES `api_token`(`id`) ON UPDATE no action ON DELETE cascade
);
