export interface paths {
    "/api/version": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["version_api_version_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/matrix": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["matrix_api_matrix_get"];
        put?: never;
        post: operations["matrix_with_sources_api_matrix_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/gitflow/rules": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["gitflow_rules_api_gitflow_rules_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["list_apps_api_apps_get"];
        put?: never;
        post: operations["add_app_api_apps_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/init": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["init_app_api_apps_init_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["app_detail_api_apps__id__get"];
        put?: never;
        post?: never;
        delete: operations["remove_app_api_apps__id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/sync": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["sync_app_api_apps__id__sync_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/push": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["push_app_api_apps__id__push_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/gitflow": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["app_gitflow_api_apps__id__gitflow_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/commits": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["app_commits_api_apps__id__commits_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/tags": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["app_tags_api_apps__id__tags_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/releases": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["app_releases_api_apps__id__releases_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/branches": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["app_branches_api_apps__id__branches_get"];
        put?: never;
        post: operations["start_branch_api_apps__id__branches_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/release": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["app_release_api_apps__id__release_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/deploy": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["app_deploy_api_apps__id__deploy_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/diagnose": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["app_diagnose_api_apps__id__diagnose_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/checkout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["checkout_api_apps__id__checkout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/pull-request": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["propose_pull_request_api_apps__id__pull_request_get"];
        put?: never;
        post: operations["open_pull_request_api_apps__id__pull_request_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/manifest": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["read_manifest_api_apps__id__manifest_get"];
        put: operations["write_manifest_api_apps__id__manifest_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/cloud": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["set_cloud_api_apps__id__cloud_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/services": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["add_service_api_apps__id__services_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/changes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["changes_api_apps__id__changes_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/install": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["install_platform_api_apps__id__install_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/discard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["discard_api_apps__id__discard_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/apps/{id}/commit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["commit_api_apps__id__commit_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["me_api_v1_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/organizations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["organizations_api_v1_organizations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tokens": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["issue_api_v1_tokens_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["projects_api_v1_projects_get"];
        put?: never;
        post: operations["create_project_api_v1_projects_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/teams": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["teams_api_v1_teams_get"];
        put?: never;
        post: operations["create_team_api_v1_teams_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/members": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["members_api_v1_members_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/teams/members": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["add_team_member_api_v1_teams_members_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/team": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["assign_project_team_api_v1_projects_team_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/members/role": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["set_member_role_api_v1_members_role_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["status_api_auth_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/sign-up": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["sign_up_api_auth_sign_up_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/sign-in": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["sign_in_api_auth_sign_in_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/sign-out": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["sign_out_api_auth_sign_out_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/session": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["session_api_auth_session_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/session/organization": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["set_active_organization_api_auth_session_organization_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/sessions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["sessions_api_auth_sessions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/sessions/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete: operations["revoke_session_api_auth_sessions__id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/organizations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["create_organization_api_auth_organizations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/members": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["add_member_api_auth_members_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/device/code": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["device_code_api_auth_device_code_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/device/token": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["device_token_api_auth_device_token_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/device": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["device_request_api_auth_device_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/device/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["device_approve_api_auth_device_approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/device/deny": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["device_deny_api_auth_device_deny_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/tokens": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["tokens_api_auth_tokens_get"];
        put?: never;
        post: operations["issue_token_api_auth_tokens_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/tokens/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete: operations["revoke_token_api_auth_tokens__id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/tokens/verify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["verify_token_api_auth_tokens_verify_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        ActiveOrganizationRequest: {
            organization_id: string;
        };
        AddAppRequest: {
            url: string;
            name?: string | null;
            install?: components["schemas"]["InstallSpec"] | null;
            credentials?: components["schemas"]["SourceCredentials"] | null;
        };
        AddMemberRequest: {
            organization_id: string;
            name: string;
            email: string;
            password: string;
            role: string;
        };
        AppDetail: {
            id: string;
            url: string;
            default_branch: string;
            project: components["schemas"]["AppMeta"];
            source_host: {
                [key: string]: string;
            };
            deploy: {
                [key: string]: unknown;
            };
            release: {
                [key: string]: string;
            };
            services: {
                [key: string]: unknown;
            };
            last_version?: string | null;
            branch: string;
            latest_tag?: string | null;
            clean: boolean;
        };
        AppEntry: {
            id: string;
            name: string;
            url: string;
            path: string;
            default_branch: string;
            installed?: string[] | null;
        };
        AppInProject: {
            id: string;
            name: string;
            registry_id: string;
            source_host_id?: string | null;
            last_synced_at?: string | null;
        };
        AppMeta: {
            name: string;
            type?: string | null;
            stack?: string | null;
            template?: string | null;
            language?: string | null;
            ci?: string | null;
        };
        AppRef: {
            id: string;
            name: string;
            registry_id: string;
        };
        AppRow: {
            id: string;
            name: string;
            url: string;
            exists: boolean;
            language?: string | null;
            type?: string | null;
            last_version?: string | null;
            branch?: string | null;
        };
        AuthStatus: {
            configured: boolean;
            users: number;
        };
        Branch: {
            name: string;
            date: string;
            kind?: string | null;
            protected: boolean;
            problem?: string | null;
        };
        BranchResult: {
            branch: string;
            base: string;
            pushed: boolean;
        };
        BrowserSessionOut: {
            id: string;
            created_at: string;
            updated_at: string;
            expires_at: string;
            ip_address?: string | null;
            user_agent?: string | null;
            current: boolean;
        };
        Changes: {
            files: string[];
            clean: boolean;
        };
        CheckoutRequest: {
            branch: string;
        };
        CloudRequest: {
            target: string;
            source?: components["schemas"]["SourceSpec"] | null;
        };
        Commit: {
            sha: string;
            subject: string;
            author: string;
            date: string;
        };
        CommitBranch: {
            kind: string;
            code: string;
            slug?: string | null;
        };
        CommitPullRequest: {
            number: number;
            url: string;
        };
        CommitRequest: {
            message: string;
            push: boolean;
            branch?: components["schemas"]["CommitBranch"] | null;
            pull_request: boolean;
            credentials?: components["schemas"]["SourceCredentials"] | null;
        };
        CommitResult: {
            sha: string;
            branch: string;
            pushed: boolean;
            pull_request?: components["schemas"]["CommitPullRequest"] | null;
        };
        CreateOrganizationRequest: {
            name: string;
            slug: string;
            git_author_name?: string | null;
            git_author_email?: string | null;
        };
        CreateProjectRequest: {
            name: string;
            description: string | null;
        };
        CreateTeamRequest: {
            name: string;
            description: string | null;
        };
        Created: {
            id: string;
            name: string;
            slug: string;
        };
        DeployRequest: {
            stage?: string | null;
            dry_run: boolean;
        };
        DeployResult: {
            target: string;
            ok: boolean;
            version: string;
            url?: string | null;
            error?: string | null;
        };
        DeviceCodeOut: {
            device_code: string;
            user_code: string;
            verification_uri: string;
            verification_uri_complete: string;
            expires_in: number;
            interval: number;
        };
        DeviceCodeRequest: {
            client_id?: string | null;
            scope?: string | null;
        };
        DeviceDecision: {
            user_code: string;
            grant?: components["schemas"]["GrantIn"] | null;
        };
        DeviceDecisionOut: {
            status: string;
        };
        DeviceRequestOut: {
            status: string;
            requested: string[];
            grant: components["schemas"]["GrantOut"];
            client_id?: string | null;
            expires_at: string;
        };
        DeviceTokenOut: {
            access_token: string;
            token_type: string;
            scope: string;
            expires_in: number;
        };
        DeviceTokenRequest: {
            grant_type: string;
            device_code: string;
            client_id?: string | null;
        };
        Diagnosis: {
            ok: boolean;
            target: string;
            status: string;
            version?: string | null;
            url?: string | null;
            details: {
                [key: string]: string;
            };
        };
        GitflowReport: {
            branch: string;
            problems: string[];
            checked_commits: number;
            ok: boolean;
        };
        GitflowRules: {
            kinds: string[];
            protected: string[];
            types: string[];
        };
        GrantIn: {
            scope?: string[];
            organization_id?: string | null;
            project_id?: string | null;
            app_id?: string | null;
        };
        GrantOut: {
            scope?: string[];
            organization_id?: string | null;
            project_id?: string | null;
            app_id?: string | null;
        };
        HTTPValidationError: {
            detail?: components["schemas"]["ValidationError"][];
        };
        IdentityOut: {
            user: components["schemas"]["UserOut"];
            session: components["schemas"]["SessionOut"];
            organization?: components["schemas"]["OrganizationOut"] | null;
            organizations: components["schemas"]["OrganizationOut"][];
            role?: string | null;
            grants: {
                [key: string]: boolean;
            };
        };
        InitRequest: {
            type: string;
            stack?: string | null;
            template?: string | null;
            name: string;
            description: string;
            package_name?: string | null;
            github_owner?: string | null;
            ci?: string | null;
            cloud?: string | null;
            git_init: boolean;
            push: boolean;
            private: boolean;
            source?: components["schemas"]["SourceSpec"] | null;
            credentials?: components["schemas"]["SourceCredentials"] | null;
        };
        InitResult: {
            id: string;
            name: string;
            path: string;
            url: string;
            template: string;
            cloud?: string | null;
            pushed: boolean;
        };
        InstallSpec: {
            type: string;
            language?: string | null;
            ci?: string | null;
        };
        Installed: {
            installed: string[];
        };
        IssueRequest: {
            scope: string;
            name?: string | null;
        };
        IssueTokenRequest: {
            name: string;
            scope: string;
            organization_id?: string | null;
            project_id?: string | null;
            app_id?: string | null;
        };
        Issued: {
            token: string;
            token_type: string;
            id: string;
            scope: string;
            expires_at: string;
            organization?: {
                [key: string]: unknown;
            } | null;
            organizations?: {
                [key: string]: unknown;
            }[] | null;
            project?: components["schemas"]["Named"] | null;
            app?: components["schemas"]["AppRef"] | null;
        };
        ManifestBody: {
            content: string;
        };
        Matrix: {
            projects: components["schemas"]["MatrixProject"][];
            clouds: components["schemas"]["MatrixCloud"][];
            services: components["schemas"]["MatrixService"][];
            sources: components["schemas"]["SourceStatus"][];
        };
        MatrixCloud: {
            name: string;
            types: string[];
            languages: string[];
            description: string;
            source: string;
        };
        MatrixProject: {
            type: string;
            stack: string;
            template: string;
            default: boolean;
            description: string;
            source: string;
            plain: boolean;
        };
        MatrixService: {
            name: string;
            providers: string[];
            description: string;
            source: string;
        };
        Me: {
            user: {
                [key: string]: unknown;
            };
            organization?: {
                [key: string]: unknown;
            } | null;
            organizations?: {
                [key: string]: unknown;
            }[] | null;
            role?: string | null;
            role_label?: string | null;
            scope?: string[] | null;
            permissions: {
                [key: string]: boolean;
            };
            token?: string | null;
            project?: components["schemas"]["Named"] | null;
            app?: components["schemas"]["AppRef"] | null;
        };
        MemberAdded: {
            user_id: string;
            existed: boolean;
        };
        MemberRoleRequest: {
            user_id: string;
            role: string;
        };
        MemberRow: {
            user_id: string;
            name: string;
            email: string;
            role: string;
            role_label: string;
        };
        Named: {
            id: string;
            name: string;
        };
        Ok: {
            ok: boolean;
        };
        OrganizationOut: {
            id: string;
            name: string;
            slug: string;
        };
        OrganizationRow: {
            id: string;
            name: string;
            slug: string;
            role?: string | null;
            role_label?: string | null;
            permissions: {
                [key: string]: boolean;
            };
            grantable_scopes: string[];
        };
        ProjectRow: {
            id: string;
            name: string;
            slug: string;
            description?: string | null;
            team?: components["schemas"]["Named"] | null;
            apps: components["schemas"]["AppInProject"][];
            organization?: components["schemas"]["Named"] | null;
        };
        ProjectTeamRequest: {
            project_id: string;
            team_id?: string | null;
        };
        PullRequestProposal: {
            head: string;
            base: string;
            title: string;
            body: string;
            commits: string[];
        };
        PullRequestRequest: {
            base?: string | null;
            title?: string | null;
            body?: string | null;
            draft: boolean;
            credentials?: components["schemas"]["SourceCredentials"] | null;
        };
        PullRequestResult: {
            number: number;
            url: string;
        };
        PushRequest: {
            private: boolean;
            credentials?: components["schemas"]["SourceCredentials"] | null;
        };
        PushResult: {
            id: string;
            url: string;
        };
        Release: {
            tag: string;
            version: string;
            date: string;
            sha: string;
            subject: string;
            prerelease: boolean;
            latest: boolean;
        };
        ReleasePreview: {
            current: string;
            next: string;
            changelog: string;
            branch: string;
            prerelease: boolean;
            dry_run: boolean;
        };
        ReleaseRequest: {
            level: string;
            dry_run: boolean;
            branch?: string | null;
            component?: string | null;
            credentials?: components["schemas"]["SourceCredentials"] | null;
        };
        ServiceRequest: {
            name: string;
            provider?: string | null;
            source?: components["schemas"]["SourceSpec"] | null;
        };
        SessionOut: {
            id: string;
            token: string;
            cookie: string;
            expires_at: string;
            created_at: string;
            updated_at: string;
            ip_address?: string | null;
            user_agent?: string | null;
            active_organization_id?: string | null;
        };
        SignInRequest: {
            email: string;
            password: string;
            ip_address?: string | null;
            user_agent?: string | null;
        };
        SignUpRequest: {
            name: string;
            email: string;
            password: string;
            invitation_id?: string | null;
        };
        Signed: {
            user: components["schemas"]["UserOut"];
            session: components["schemas"]["SessionOut"];
        };
        SourceCredentials: {
            kind?: string | null;
            token?: string | null;
            username?: string | null;
            base_url?: string | null;
            author_name?: string | null;
            author_email?: string | null;
            owner?: string | null;
        };
        SourceSpec: {
            name: string;
            url: string;
            ref: string;
            credentials?: components["schemas"]["SourceCredentials"] | null;
        };
        SourceStatus: {
            name: string;
            url: string;
            ref: string;
            ok: boolean;
            error?: string | null;
            projects: number;
            clouds: number;
            services: number;
        };
        SourcesRequest: {
            sources: components["schemas"]["SourceSpec"][];
        };
        StartBranchRequest: {
            kind: string;
            code: string;
            slug?: string | null;
            push: boolean;
            credentials?: components["schemas"]["SourceCredentials"] | null;
        };
        SyncRequest: {
            credentials?: components["schemas"]["SourceCredentials"] | null;
            reset: boolean;
        };
        TeamMemberRequest: {
            team_id: string;
            user_id: string;
        };
        TeamMemberRow: {
            userId: string;
            name: string;
            email: string;
        };
        TeamRow: {
            id: string;
            name: string;
            slug: string;
            description?: string | null;
            members: components["schemas"]["TeamMemberRow"][];
            projects: components["schemas"]["Named"][];
        };
        TokenClaimsOut: {
            id: string;
            user: components["schemas"]["UserOut"];
            organization?: components["schemas"]["OrganizationOut"] | null;
            organizations: components["schemas"]["OrganizationOut"][];
            all_organizations: boolean;
            scope: string[];
            project_id?: string | null;
            app_id?: string | null;
            role?: string | null;
        };
        TokenClientOut: {
            name: string;
            first_seen_at: string;
            last_seen_at: string;
        };
        TokenIssued: {
            id: string;
            token: string;
            scope: string[];
            expires_at: string;
        };
        TokenOut: {
            id: string;
            name: string;
            scope: string[];
            organization?: components["schemas"]["Named"] | null;
            project?: components["schemas"]["Named"] | null;
            app?: components["schemas"]["Named"] | null;
            created_at: string;
            expires_at: string;
            last_used_at?: string | null;
            clients: components["schemas"]["TokenClientOut"][];
        };
        UserOut: {
            id: string;
            name: string;
            email: string;
            image?: string | null;
        };
        ValidationError: {
            loc: (string | number)[];
            msg: string;
            type: string;
            input?: unknown;
            ctx?: Record<string, never>;
        };
        VerifyTokenRequest: {
            token: string;
            client?: string | null;
        };
        Version: {
            version: string;
            api: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    version_api_version_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Version"];
                };
            };
        };
    };
    matrix_api_matrix_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Matrix"];
                };
            };
        };
    };
    matrix_with_sources_api_matrix_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SourcesRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Matrix"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    gitflow_rules_api_gitflow_rules_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GitflowRules"];
                };
            };
        };
    };
    list_apps_api_apps_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AppRow"][];
                };
            };
        };
    };
    add_app_api_apps_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AddAppRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AppEntry"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    init_app_api_apps_init_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InitRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InitResult"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    app_detail_api_apps__id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AppDetail"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    remove_app_api_apps__id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sync_app_api_apps__id__sync_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["SyncRequest"] | null;
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AppEntry"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    push_app_api_apps__id__push_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PushRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PushResult"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    app_gitflow_api_apps__id__gitflow_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GitflowReport"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    app_commits_api_apps__id__commits_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Commit"][];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    app_tags_api_apps__id__tags_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": string[];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    app_releases_api_apps__id__releases_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Release"][];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    app_branches_api_apps__id__branches_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Branch"][];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    start_branch_api_apps__id__branches_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StartBranchRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BranchResult"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    app_release_api_apps__id__release_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReleaseRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReleasePreview"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    app_deploy_api_apps__id__deploy_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DeployRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeployResult"][];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    app_diagnose_api_apps__id__diagnose_get: {
        parameters: {
            query?: {
                stage?: string | null;
            };
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Diagnosis"][];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    checkout_api_apps__id__checkout_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CheckoutRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    propose_pull_request_api_apps__id__pull_request_get: {
        parameters: {
            query?: {
                base?: string | null;
                title?: string | null;
            };
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PullRequestProposal"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    open_pull_request_api_apps__id__pull_request_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PullRequestRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PullRequestResult"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_manifest_api_apps__id__manifest_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ManifestBody"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    write_manifest_api_apps__id__manifest_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ManifestBody"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ManifestBody"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    set_cloud_api_apps__id__cloud_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CloudRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_service_api_apps__id__services_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ServiceRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    changes_api_apps__id__changes_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Changes"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    install_platform_api_apps__id__install_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["InstallSpec"] | null;
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Installed"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    discard_api_apps__id__discard_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Changes"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    commit_api_apps__id__commit_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CommitRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommitResult"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    me_api_v1_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Me"];
                };
            };
        };
    };
    organizations_api_v1_organizations_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OrganizationRow"][];
                };
            };
        };
    };
    issue_api_v1_tokens_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IssueRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Issued"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    projects_api_v1_projects_get: {
        parameters: {
            query?: {
                organization?: string | null;
            };
            header?: {
                "x-organization"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectRow"][];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_project_api_v1_projects_post: {
        parameters: {
            query?: never;
            header?: {
                "x-organization"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateProjectRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Created"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    teams_api_v1_teams_get: {
        parameters: {
            query?: {
                organization?: string | null;
            };
            header?: {
                "x-organization"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamRow"][];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_team_api_v1_teams_post: {
        parameters: {
            query?: never;
            header?: {
                "x-organization"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateTeamRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Created"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    members_api_v1_members_get: {
        parameters: {
            query?: {
                organization?: string | null;
            };
            header?: {
                "x-organization"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemberRow"][];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_team_member_api_v1_teams_members_post: {
        parameters: {
            query?: never;
            header?: {
                "x-organization"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TeamMemberRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Ok"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    assign_project_team_api_v1_projects_team_post: {
        parameters: {
            query?: never;
            header?: {
                "x-organization"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectTeamRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Ok"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    set_member_role_api_v1_members_role_post: {
        parameters: {
            query?: never;
            header?: {
                "x-organization"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MemberRoleRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Ok"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    status_api_auth_status_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthStatus"];
                };
            };
        };
    };
    sign_up_api_auth_sign_up_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SignUpRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Signed"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sign_in_api_auth_sign_in_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SignInRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Signed"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sign_out_api_auth_sign_out_post: {
        parameters: {
            query?: never;
            header?: {
                "x-session-token"?: string | null;
                "x-session-cookie"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    session_api_auth_session_get: {
        parameters: {
            query?: never;
            header?: {
                "x-session-token"?: string | null;
                "x-session-cookie"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IdentityOut"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    set_active_organization_api_auth_session_organization_post: {
        parameters: {
            query?: never;
            header?: {
                "x-session-token"?: string | null;
                "x-session-cookie"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ActiveOrganizationRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IdentityOut"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sessions_api_auth_sessions_get: {
        parameters: {
            query?: never;
            header?: {
                "x-session-token"?: string | null;
                "x-session-cookie"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BrowserSessionOut"][];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    revoke_session_api_auth_sessions__id__delete: {
        parameters: {
            query?: never;
            header?: {
                "x-session-token"?: string | null;
                "x-session-cookie"?: string | null;
            };
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_organization_api_auth_organizations_post: {
        parameters: {
            query?: never;
            header?: {
                "x-session-token"?: string | null;
                "x-session-cookie"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateOrganizationRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OrganizationOut"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_member_api_auth_members_post: {
        parameters: {
            query?: never;
            header?: {
                "x-session-token"?: string | null;
                "x-session-cookie"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AddMemberRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemberAdded"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    device_code_api_auth_device_code_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DeviceCodeRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeviceCodeOut"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    device_token_api_auth_device_token_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DeviceTokenRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeviceTokenOut"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    device_request_api_auth_device_get: {
        parameters: {
            query: {
                user_code: string;
            };
            header?: {
                "x-session-token"?: string | null;
                "x-session-cookie"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeviceRequestOut"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    device_approve_api_auth_device_approve_post: {
        parameters: {
            query?: never;
            header?: {
                "x-session-token"?: string | null;
                "x-session-cookie"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DeviceDecision"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeviceDecisionOut"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    device_deny_api_auth_device_deny_post: {
        parameters: {
            query?: never;
            header?: {
                "x-session-token"?: string | null;
                "x-session-cookie"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DeviceDecision"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeviceDecisionOut"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    tokens_api_auth_tokens_get: {
        parameters: {
            query?: {
                organization_id?: string | null;
            };
            header?: {
                "x-session-token"?: string | null;
                "x-session-cookie"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TokenOut"][];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    issue_token_api_auth_tokens_post: {
        parameters: {
            query?: never;
            header?: {
                "x-session-token"?: string | null;
                "x-session-cookie"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IssueTokenRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TokenIssued"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    revoke_token_api_auth_tokens__id__delete: {
        parameters: {
            query?: never;
            header?: {
                "x-session-token"?: string | null;
                "x-session-cookie"?: string | null;
            };
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    verify_token_api_auth_tokens_verify_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VerifyTokenRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TokenClaimsOut"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
