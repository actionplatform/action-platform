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
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        AddAppRequest: {
            url: string;
            name?: string | null;
            install?: components["schemas"]["InstallSpec"] | null;
            credentials?: components["schemas"]["SourceCredentials"] | null;
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
        AppMeta: {
            name: string;
            type?: string | null;
            stack?: string | null;
            template?: string | null;
            language?: string | null;
            ci?: string | null;
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
        HTTPValidationError: {
            detail?: components["schemas"]["ValidationError"][];
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
        ValidationError: {
            loc: (string | number)[];
            msg: string;
            type: string;
            input?: unknown;
            ctx?: Record<string, never>;
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
}
