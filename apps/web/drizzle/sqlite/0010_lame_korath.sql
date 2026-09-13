CREATE TABLE `organization_setting` (
	`organization_id` text PRIMARY KEY NOT NULL,
	`git_author_name` text NOT NULL,
	`git_author_email` text NOT NULL,
	`updated_at` integer NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organization`(`id`) ON UPDATE no action ON DELETE cascade
);
