# Azure and Helm Chart Security Rules

## Azure Terraform Security Rules

### AZ-STORAGE-001: Storage Account Public Access
**Severity:** CRITICAL  
**Category:** Security  
**Description:** Azure storage accounts should not allow public blob access

**Rule:**
```hcl
# Bad
resource "azurerm_storage_account" "example" {
  name                     = "storageaccount1"
  account_tier             = "Standard"
  account_replication_type = "LRS"
  allow_blob_public_access = true  # ❌
}

# Good
resource "azurerm_storage_account" "example" {
  name                     = "storageaccount1"
  account_tier             = "Standard"
  account_replication_type = "LRS"
  allow_blob_public_access = false  # ✅
}
```

**Remediation:** Set `allow_blob_public_access = false`

---

### AZ-STORAGE-002: Storage Account Encryption
**Severity:** HIGH  
**Category:** Security  
**Description:** Storage accounts must have encryption enabled

**Rule:**
```hcl
# Bad
resource "azurerm_storage_account" "example" {
  name                     = "storageaccount1"
  account_tier             = "Standard"
  account_replication_type = "LRS"
  # Missing encryption block ❌
}

# Good
resource "azurerm_storage_account" "example" {
  name                     = "storageaccount1"
  account_tier             = "Standard"
  account_replication_type = "LRS"
  
  network_rules {
    default_action = "Deny"  # ✅
  }
}
```

**Remediation:** Add network rules with deny default action

---

### AZ-NETWORK-001: NSG Missing Inbound Rules
**Severity:** HIGH  
**Category:** Security  
**Description:** Network Security Groups should restrict inbound access

**Rule:**
```hcl
# Bad
resource "azurerm_network_security_group" "example" {
  name                = "example-nsg"
  location            = azurerm_resource_group.example.location
  resource_group_name = azurerm_resource_group.example.name
  
  # No security rules defined ❌
}

# Good
resource "azurerm_network_security_group" "example" {
  name                = "example-nsg"
  location            = azurerm_resource_group.example.location
  resource_group_name = azurerm_resource_group.example.name
  
  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}
```

**Remediation:** Define explicit security rules with least privilege

---

### AZ-NETWORK-002: SQL Server Firewall Open to Internet
**Severity:** CRITICAL  
**Category:** Security  
**Description:** SQL Server firewall should not allow access from 0.0.0.0

**Rule:**
```hcl
# Bad
resource "azurerm_sql_firewall_rule" "example" {
  name                = "AllowAll"
  resource_group_name = azurerm_resource_group.example.name
  server_name         = azurerm_sql_server.example.name
  start_ip_address    = "0.0.0.0"  # ❌
  end_ip_address      = "255.255.255.255"
}

# Good
resource "azurerm_sql_firewall_rule" "example" {
  name                = "AllowSpecific"
  resource_group_name = azurerm_resource_group.example.name
  server_name         = azurerm_sql_server.example.name
  start_ip_address    = "10.0.0.1"  # ✅
  end_ip_address      = "10.0.0.10"
}
```

**Remediation:** Restrict firewall rules to specific IP ranges

---

### AZ-IAM-001: Overly Permissive RBAC
**Severity:** HIGH  
**Category:** Security  
**Description:** Role assignments should not use Contributor role at subscription level

**Rule:**
```hcl
# Bad
resource "azurerm_role_assignment" "example" {
  scope                = "/subscriptions/{subscription-id}"  # ❌ Too broad
  role_definition_name = "Contributor"
  principal_id         = azurerm_user.example.id
}

# Good
resource "azurerm_role_assignment" "example" {
  scope                = "/subscriptions/{subscription-id}/resourceGroups/myResourceGroup"  # ✅
  role_definition_name = "Reader"
  principal_id         = azurerm_user.example.id
}
```

**Remediation:** Use least privilege scope and role

---

### AZ-IAM-002: Managed Identity Not Enabled
**Severity:** MEDIUM  
**Category:** Security  
**Description:** App Services should use managed identities

**Rule:**
```hcl
# Bad
resource "azurerm_app_service" "example" {
  name                = "example-appservice"
  location            = azurerm_resource_group.example.location
  resource_group_name = azurerm_resource_group.example.name
  app_service_plan_id = azurerm_app_service_plan.example.id
  # Missing identity block ❌
}

# Good
resource "azurerm_app_service" "example" {
  name                = "example-appservice"
  location            = azurerm_resource_group.example.location
  resource_group_name = azurerm_resource_group.example.name
  app_service_plan_id = azurerm_app_service_plan.example.id
  
  identity {
    type = "SystemAssigned"  # ✅
  }
}
```

**Remediation:** Enable system-assigned managed identity

---

### AZ-KEYVAULT-001: Key Vault Public Access
**Severity:** CRITICAL  
**Category:** Security  
**Description:** Key Vault should not be accessible from public internet

**Rule:**
```hcl
# Bad
resource "azurerm_key_vault" "example" {
  name                = "examplekv"
  location            = azurerm_resource_group.example.location
  resource_group_name = azurerm_resource_group.example.name
  tenant_id           = azurerm_client_config.example.tenant_id
  sku_name            = "standard"
  
  network_acls {
    default_action = "Allow"  # ❌
    bypass         = "AzureServices"
  }
}

# Good
resource "azurerm_key_vault" "example" {
  name                = "examplekv"
  location            = azurerm_resource_group.example.location
  resource_group_name = azurerm_resource_group.example.name
  tenant_id           = azurerm_client_config.example.tenant_id
  sku_name            = "standard"
  
  network_acls {
    default_action = "Deny"  # ✅
    bypass         = "AzureServices"
  }
}
```

**Remediation:** Set network ACL default action to Deny

---

### AZ-LOG-001: Diagnostic Logging Not Enabled
**Severity:** MEDIUM  
**Category:** Observability  
**Description:** Azure resources should have diagnostic logging enabled

**Rule:**
```hcl
# Bad
resource "azurerm_key_vault" "example" {
  name                = "examplekv"
  # Missing diagnostic_settings ❌
}

# Good
resource "azurerm_monitor_diagnostic_setting" "example" {
  name                       = "example-setting"
  target_resource_id         = azurerm_key_vault.example.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.example.id
  
  enabled_log {
    category = "AuditEvent"
  }
}
```

**Remediation:** Add diagnostic settings for all resources

---

## Helm Chart Security Rules

### HELM-SEC-001: Container Running as Root
**Severity:** CRITICAL  
**Category:** Security  
**Description:** Containers should not run as root user

**Rule:**
```yaml
# Bad - values.yaml
securityContext:
  runAsRoot: true  # ❌
  runAsUser: 0     # ❌

# Good - values.yaml
securityContext:
  runAsNonRoot: true  # ✅
  runAsUser: 1000     # ✅
  fsGroup: 1000       # ✅
```

**Remediation:** Set `runAsNonRoot: true` and non-root `runAsUser`

---

### HELM-SEC-002: Privileged Container
**Severity:** CRITICAL  
**Category:** Security  
**Description:** Containers should not run in privileged mode

**Rule:**
```yaml
# Bad - values.yaml
securityContext:
  privileged: true  # ❌

# Good - values.yaml
securityContext:
  privileged: false  # ✅
  allowPrivilegeEscalation: false  # ✅
```

**Remediation:** Disable privileged mode and privilege escalation

---

### HELM-SEC-003: Missing Pod Security Policy
**Severity:** HIGH  
**Category:** Security  
**Description:** Helm charts should define pod security policies

**Rule:**
```yaml
# Bad - templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: app
        # No securityContext ❌

# Good - templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      containers:
      - name: app
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
```

**Remediation:** Add securityContext at pod and container level

---

### HELM-REL-001: Missing Resource Limits
**Severity:** HIGH  
**Category:** Reliability  
**Description:** Containers must have resource limits defined

**Rule:**
```yaml
# Bad - values.yaml
resources: {}  # ❌

# Good - values.yaml
resources:
  limits:
    cpu: 500m    # ✅
    memory: 512Mi  # ✅
  requests:
    cpu: 250m    # ✅
    memory: 256Mi  # ✅
```

**Remediation:** Define CPU and memory limits/requests

---

### HELM-REL-002: Missing Liveness/Readiness Probes
**Severity:** MEDIUM  
**Category:** Reliability  
**Description:** Containers should have health probes defined

**Rule:**
```yaml
# Bad - values.yaml
livenessProbe: {}   # ❌
readinessProbe: {}  # ❌

# Good - values.yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

**Remediation:** Define liveness and readiness probes

---

### HELM-REL-003: Single Replica Deployment
**Severity:** MEDIUM  
**Category:** Reliability  
**Description:** Production deployments should have multiple replicas

**Rule:**
```yaml
# Bad - values.yaml
replicaCount: 1  # ❌

# Good - values.yaml
replicaCount: 3  # ✅
```

**Remediation:** Set replica count to 2 or more for production

---

### HELM-VER-001: Chart Version Not Pinned
**Severity:** LOW  
**Category:** Reliability  
**Description:** Chart dependencies should use pinned versions

**Rule:**
```yaml
# Bad - Chart.yaml
dependencies:
  - name: redis
    repository: https://charts.bitnami.com/bitnami
    version: "*"  # ❌

# Good - Chart.yaml
dependencies:
  - name: redis
    repository: https://charts.bitnami.com/bitnami
    version: "16.10.0"  # ✅
```

**Remediation:** Pin dependency versions

---

### HELM-IMG-001: Image Tag Not Pinned
**Severity:** HIGH  
**Category:** Security  
**Description:** Container images should use pinned tags (not latest)

**Rule:**
```yaml
# Bad - values.yaml
image:
  repository: myapp
  tag: latest  # ❌

# Good - values.yaml
image:
  repository: myapp
  tag: v1.2.3  # ✅
```

**Remediation:** Use specific version tags instead of `latest`

---

### HELM-SEC-004: Missing Network Policy
**Severity:** MEDIUM  
**Category:** Security  
**Description:** Helm charts should define network policies

**Rule:**
```yaml
# Bad - No network policy templates

# Good - templates/networkpolicy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ .Release.Name }}-network-policy
spec:
  podSelector:
    matchLabels:
      app: {{ .Release.Name }}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: {{ .Release.Name }}
```

**Remediation:** Add NetworkPolicy templates

---

## Implementation Priority

### Phase 1: Critical Security Rules
1. AZ-STORAGE-001 - Storage public access
2. AZ-NETWORK-002 - SQL firewall open
3. AZ-KEYVAULT-001 - Key Vault public access
4. HELM-SEC-001 - Container as root
5. HELM-SEC-002 - Privileged container

### Phase 2: High Severity Rules
1. AZ-STORAGE-002 - Storage encryption
2. AZ-NETWORK-001 - NSG missing rules
3. AZ-IAM-001 - Overly permissive RBAC
4. HELM-REL-001 - Missing resource limits
5. HELM-IMG-001 - Image tag not pinned

### Phase 3: Medium/Low Severity Rules
1. AZ-IAM-002 - Managed identity
2. AZ-LOG-001 - Diagnostic logging
3. HELM-REL-002 - Missing probes
4. HELM-REL-003 - Single replica
5. HELM-VER-001 - Version not pinned
6. HELM-SEC-004 - Missing network policy

---

## Testing Strategy

### Unit Tests
1. Test each rule with valid/invalid examples
2. Test file detection (Azure .tf files, Helm charts)
3. Test severity assignment

### Integration Tests
1. Test with real Azure Terraform repositories
2. Test with real Helm chart repositories
3. Test scan performance with large repos

### End-to-End Tests
1. Full scan workflow
2. Frontend display of findings
3. AI remediation suggestions
