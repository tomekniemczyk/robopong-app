## API Design

### RESTful Principles
Use resource-based URLs with appropriate HTTP methods (GET, POST, PUT, PATCH, DELETE).

### Consistent Naming
Use lowercase, hyphenated or underscored names consistently across endpoints.

### Versioning
Implement versioning (URL path or headers) to manage breaking changes.

### Plural Nouns
Use plural nouns for resources (`/users`, `/products`).

### Limited Nesting
Keep URL nesting to 2-3 levels maximum for readability.

### Query Parameters
Use query parameters for filtering, sorting, and pagination.

### Proper Status Codes
Return appropriate HTTP status codes (200, 201, 400, 404, 500).

### Rate Limit Headers
Include rate limit information in response headers.

### REST Endpoints Under /api/ with Plural Resources
All REST endpoints use `/api/` prefix with plural nouns. Multi-word resources use kebab-case: `/api/training-history`, `/api/voice-notes`, `/api/ball-landings`.

### HTTP Status Code Convention
POST create returns 201. DELETE returns 204. PUT side-effects return 204. GET returns 200 (default). Explicit `status_code=` on decorators.

### HTTPException Pattern
404 errors: bare `raise HTTPException(404)`. 400/403/409: include message: `raise HTTPException(403, "Cannot delete readonly folder")`.
