# E2E Testing Guide — Open Data Platform UI

## Overview

This guide describes how to test the complete end-to-end workflows in the ODP frontend. E2E tests verify that the entire system works as expected when users interact with the UI, from data ingestion through visualization.

## Prerequisites

- All services running: `make up`
- Sample data seeded: `make seed`
- Frontend development server running: `cd frontend && npm run dev`
- Services accessible at `http://localhost:8000` (API) and `http://localhost:3000` (frontend)

## Core Workflows to Test

### 1. **Data Upload Workflow**

Tests that users can upload CSV files and they appear in the system.

**Steps:**
1. Navigate to Datasets page
2. Drag-drop (or click to select) a CSV file
3. Verify file appears in datasets table
4. Click dataset to view schema
5. Verify schema was inferred correctly
6. Click "Preview" to view sample rows

**Expected outcomes:**
- File uploaded and visible in MinIO
- Schema metadata stored in PostgreSQL
- First N rows parseable and displayed

**Test data:** Use `examples/sample-data/customers.csv`

---

### 2. **Ontology Definition Workflow**

Tests that users can create semantic types and define relationships.

**Steps:**
1. Navigate to Ontology Explorer page
2. Click "Create Object Type"
3. Enter name: "Customer"
4. Add properties:
   - `customer_id` (UUID)
   - `name` (String)
   - `email` (String)
   - `created_at` (Timestamp)
5. Save and verify type appears in graph

**Expected outcomes:**
- ObjectType node created in Neo4j
- Properties stored correctly
- Graph visualization updates with new node

---

### 3. **Dataset-to-Ontology Mapping Workflow**

Tests that users can map uploaded data to semantic types.

**Steps:**
1. From Datasets page, select the Customer dataset
2. Click "Map to Ontology Type"
3. Select "Customer" object type
4. Map columns to properties:
   - CSV `id` → Customer `customer_id`
   - CSV `name` → Customer `name`
   - CSV `email` → Customer `email`
   - CSV `created_at` → Customer `created_at`
5. Click "Create Mapping"
6. Verify mapping succeeds

**Expected outcomes:**
- ObjectInstances created in Neo4j from dataset rows
- Mapping metadata stored in PostgreSQL
- Graph now shows Customer instances (or instance count updates)

---

### 4. **Pipeline Execution Workflow**

Tests that users can trigger data transformation pipelines.

**Steps:**
1. Navigate to Pipelines page
2. Click "Run Pipeline" on the sample pipeline
3. Monitor run status in real-time
4. When complete, view run logs
5. Click dataset to verify transformed data in ClickHouse

**Expected outcomes:**
- Pipeline execution initiated in Dagster
- Run status transitions from pending → running → completed
- Logs visible in UI
- Transformed data queryable in ClickHouse

---

### 5. **Data Explorer Workflow**

Tests that users can query and analyze data using SQL.

**Note:** Tables are created by the pipeline and named `analytics_{dataset}`. Run the pipeline (workflow 4) before testing queries here.

**Steps:**
1. Navigate to Data Explorer page
2. Enter SQL query: `SELECT COUNT(*) as total FROM analytics_customers LIMIT 100`
3. Click "Execute"
4. Verify results table displays with one row and column `total`
5. Update query with WHERE clause: `SELECT * FROM analytics_customers WHERE country = 'US' LIMIT 10`
6. Execute and verify filtered results

**Expected outcomes:**
- Query executes against ClickHouse
- Results table renders with correct columns and rows
- Errors handled gracefully if query is invalid

---

### 6. **Ontology Graph Interaction Workflow**

Tests that the graph visualization is interactive.

**Steps:**
1. Navigate to Ontology Explorer page
2. Verify force-directed graph renders
3. Click a node (e.g., Customer type)
4. Verify node is highlighted and properties panel opens
5. Drag a node and verify it moves
6. Zoom in/out (scroll wheel)
7. Pan (click and drag canvas)

**Expected outcomes:**
- Graph renders without errors
- Node selection works
- Graph interactions are smooth (no freezing)
- Properties panel displays accurate data

---

## Testing Approach

### Option A: Manual Testing Checklist

For rapid iteration during development, use this checklist before each release:

```markdown
- [ ] Upload CSV → appears in datasets
- [ ] View schema inference
- [ ] Preview dataset rows
- [ ] Create object type
- [ ] Map dataset to type
- [ ] Trigger pipeline
- [ ] View pipeline logs
- [ ] Execute SQL query
- [ ] Interact with graph (click, drag, zoom)
- [ ] Navigate all pages without errors
- [ ] No browser console errors
```

### Option B: Automated E2E Tests (Playwright)

For comprehensive automated testing, use Playwright:

**Install dependencies:**
```bash
cd frontend
npm install -D @playwright/test
npx playwright install
```

**Create test file:** `frontend/e2e/workflows.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('ODP E2E Workflows', () => {
  test.beforeEach(async ({ page }) => {
    // Start at the dashboard
    await page.goto('http://localhost:3000');
    // Wait for API to be ready
    await page.waitForLoadState('networkidle');
  });

  test('Upload dataset workflow', async ({ page }) => {
    // Navigate to Datasets
    await page.click('a[href="/datasets"]');
    await page.waitForLoadState('networkidle');

    // Upload file (assuming file input exists)
    const fileInput = await page.locator('input[type="file"]');
    await fileInput.setInputFiles('examples/sample-data/customers.csv');
    
    // Wait for upload to complete
    await page.waitForSelector('[data-testid="dataset-row-customers"]', { timeout: 10000 });
    
    // Verify dataset appears
    const datasetRow = page.locator('[data-testid="dataset-row-customers"]');
    await expect(datasetRow).toBeVisible();
  });

  test('Create ontology type workflow', async ({ page }) => {
    // Navigate to Ontology Explorer
    await page.click('a[href="/ontology"]');
    await page.waitForLoadState('networkidle');

    // Click create button
    await page.click('button:has-text("Create Object Type")');
    
    // Fill form
    await page.fill('[name="typeName"]', 'Customer');
    await page.fill('[name="description"]', 'Test customer type');
    
    // Add properties
    await page.click('button:has-text("Add Property")');
    await page.fill('[name="propertyName"]', 'customer_id');
    await page.selectOption('[name="propertyType"]', 'UUID');
    
    // Save
    await page.click('button:has-text("Save")');
    
    // Verify type appears in graph
    await page.waitForSelector('[data-testid="graph-node-customer"]', { timeout: 5000 });
    const node = page.locator('[data-testid="graph-node-customer"]');
    await expect(node).toBeVisible();
  });

  test('Query data in explorer', async ({ page }) => {
    // Navigate to Data Explorer
    await page.click('a[href="/explorer"]');
    await page.waitForLoadState('networkidle');

    // Enter query
    const editor = page.locator('[data-testid="sql-editor"]');
    await editor.click();
    await editor.fill('SELECT COUNT(*) as total FROM analytics_customers');
    
    // Execute
    await page.click('button:has-text("Execute")');
    
    // Wait for results
    await page.waitForSelector('[data-testid="results-table"]', { timeout: 5000 });
    
    // Verify results
    const resultsTable = page.locator('[data-testid="results-table"]');
    await expect(resultsTable).toBeVisible();
    
    // Verify row count (should be >= 1)
    const rows = page.locator('[data-testid="results-table"] tbody tr');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });

  test('Ontology graph interaction', async ({ page }) => {
    // Navigate to Ontology Explorer
    await page.click('a[href="/ontology"]');
    await page.waitForLoadState('networkidle');

    // Verify graph renders
    const graph = page.locator('[data-testid="force-graph"]');
    await expect(graph).toBeVisible();

    // Click a node
    const nodes = page.locator('[data-testid*="graph-node"]');
    if (await nodes.count() > 0) {
      await nodes.first().click();
      
      // Verify properties panel opens
      const propertiesPanel = page.locator('[data-testid="properties-panel"]');
      await expect(propertiesPanel).toBeVisible();
    }
  });

  test('Pipeline execution workflow', async ({ page }) => {
    // Navigate to Pipelines
    await page.click('a[href="/pipelines"]');
    await page.waitForLoadState('networkidle');

    // Trigger pipeline
    await page.click('button:has-text("Run Pipeline")');
    
    // Wait for modal/confirmation
    await page.click('button:has-text("Confirm")');
    
    // Poll for completion (with timeout)
    let completed = false;
    for (let i = 0; i < 60; i++) {
      const status = await page.textContent('[data-testid="latest-run-status"]');
      if (status === 'Completed' || status === 'Failed') {
        completed = true;
        break;
      }
      await page.waitForTimeout(1000);
    }
    
    expect(completed).toBe(true);
    
    // View logs
    await page.click('[data-testid="view-logs-button"]');
    const logsPanel = page.locator('[data-testid="logs-panel"]');
    await expect(logsPanel).toBeVisible();
  });
});
```

**Run tests:**
```bash
cd frontend
npm run test:e2e              # Run all tests
npm run test:e2e -- --headed  # Run with UI visible
npm run test:e2e -- --debug   # Debug mode
```

**Add to package.json:**
```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:headed": "playwright test --headed",
    "test:e2e:debug": "playwright test --debug"
  }
}
```

---

### Option C: Cypress (Alternative)

If you prefer Cypress, install and configure:

```bash
cd frontend
npm install -D cypress
npx cypress open
```

Then create tests in `frontend/cypress/e2e/workflows.cy.ts` with similar structure.

---

## Test Data

Sample datasets are provided in `examples/sample-data/`:
- `customers.csv` — customer records (id, name, email, created_at)
- `orders.csv` — orders (order_id, customer_id, amount, date)
- `products.csv` — products (product_id, name, price)

These can be used in both manual and automated tests.

---

## Debugging Failed Tests

### Issue: Dataset upload times out
- **Check:** MinIO is running (`docker ps | grep minio`)
- **Check:** File path is correct (relative to `frontend/` directory)
- **Solution:** Add longer timeout: `await page.waitForSelector(..., { timeout: 30000 })`

### Issue: Graph doesn't render
- **Check:** API is returning graph data (`curl http://localhost:8000/api/v1/ontology/graph`)
- **Check:** Browser console for errors (F12 → Console tab)
- **Solution:** Increase wait time, verify data structure matches expectations

### Issue: Query returns no results
- **Check:** Sample data was seeded (`make seed`)
- **Check:** Query syntax is valid
- **Solution:** Test query directly with `curl` or database client first

### Issue: Pipeline never completes
- **Check:** Dagster is running (`curl http://localhost:3001/`)
- **Check:** Pipeline logs in Dagster UI for errors
- **Solution:** Increase polling timeout in test, check for stuck runs

---

## CI/CD Integration

To run E2E tests in CI/CD pipeline:

```yaml
# .github/workflows/e2e.yml
name: E2E Tests
on: [push, pull_request]
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - run: npm ci
      - run: docker-compose up -d
      - run: npm run test:e2e
      - uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
```

---

## Best Practices

1. **Use test IDs:** Add `data-testid` attributes to key elements for reliable selectors
2. **Wait for network:** Use `waitForLoadState('networkidle')` after navigation
3. **Avoid hardcoded waits:** Prefer `waitForSelector` over `waitForTimeout`
4. **Test happy path first:** Start with the main workflow, edge cases second
5. **Keep tests independent:** Each test should set up its own data
6. **Fail fast:** If setup fails, skip remaining steps rather than cascading failures
7. **Document expected outcomes:** Include comments explaining what should happen

---

## Acceptance Criteria

All E2E tests pass when:
- [ ] All workflows execute without errors
- [ ] Data persists across page reloads
- [ ] UI reflects backend state correctly
- [ ] No browser console errors
- [ ] Performance is acceptable (<5s per workflow)

---

## References

- [Playwright Documentation](https://playwright.dev)
- [Cypress Documentation](https://docs.cypress.io)
- [ODP Architecture](./architecture.md)
- [API Documentation](../services/api-gateway/README.md)
