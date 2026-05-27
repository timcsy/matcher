# Feature Specification: 部署到 K8s（本機 k3s 叢集）

**Feature Branch**: `020-k8s-deploy`
**Created**: 2026-05-27
**Status**: Draft
**Input**: 階段 5——把 matcher 部署到本機 k8s（k3s + 現有 kubectl）：單一容器、PVC 持久化、無 DB；Google 登入沿用現有 client id（機密由操作者本機 .env 灌入）；網域/TLS 由使用者自理。

## 背景與動機

vision 階段 5 是唯一剩下的里程碑：把已完成的 Web 應用容器化、部署到 K8s，讓學校能在自有叢集上實際使用。架構維持「單一容器 + 檔案系統儲存 + 無 DB」（vision 架構段），登入維持現有 Google OAuth（階段 6）。此 feature 是**純打包與部署**，不改動 `src/matcher`。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 操作者把應用部署到叢集並能存取（Priority: P1）

學校的操作者（你）用本機 kubectl，把 matcher 部署到叢集，並能在本機開啟它的網頁。

**Why this priority**: 沒有「跑得起來且打得開」，其餘都無從談起，是 MVP。

**Independent Test**: 套用部署資源後，工作負載進入就緒狀態；從本機存取點開啟首頁回應正常。

**Acceptance Scenarios**:

1. **Given** 本機 kubectl 指向可用叢集，**When** 操作者套用部署資源，**Then** 應用工作負載就緒、本機存取點可開啟首頁。
2. **Given** 應用已就緒，**When** 開啟一般頁面，**Then** 頁面正常顯示（含需要 PDF 渲染的稽核報告下載可用）。

---

### User Story 2 - 使用者用現有 Google 帳號登入並完成配對（Priority: P1）

被授權的使用者透過 Google 登入，沿用**現有的** OAuth client id，不必為了本機部署另外改 Google 設定，登入後能跑完一次配對。

**Why this priority**: 登入是公開使用的前置；「沿用現有 client id」是使用者明確要求。

**Independent Test**: 從本機存取點走一次 Google 登入流程，成功後上傳/填一份清單跑出配對結果。

**Acceptance Scenarios**:

1. **Given** 應用已部署且機密已提供，**When** 使用者經由本機存取點登入 Google，**Then** 登入成功、導回應用、看得到自己的管理頁。
2. **Given** 已登入，**When** 執行一次配對，**Then** 產出可檢視的結果與可下載的稽核紀錄。

---

### User Story 3 - 重啟後資料不遺失（Priority: P2）

工作負載被重啟或重新排程後，先前產生的配對紀錄與自訂範本仍然存在。

**Why this priority**: vision 階段 5 明列「重啟後資料與稽核紀錄不遺失」為成功標準；對「可稽核」是基本要求。

**Independent Test**: 跑出一筆配對 + 建一個自訂範本 → 刪除工作負載 pod 使其重建 → 兩者仍可查得到。

**Acceptance Scenarios**:

1. **Given** 已有配對紀錄與自訂範本，**When** 工作負載 pod 被刪除並由叢集重建，**Then** 紀錄與範本 100% 保留、可正常開啟。

---

### User Story 4 - 機密不外洩（Priority: P2）

OAuth client secret 與簽章金鑰只存在於叢集機密中（來源為操作者本機 .env），不出現在版本控制或容器映像裡。

**Why this priority**: 原則 6（資料保護）——公開使用承載個資的前提是保護憑證。

**Independent Test**: 檢查版本控制追蹤的所有檔案與容器映像，皆無真實機密值；機密只能在叢集 Secret 中查得。

**Acceptance Scenarios**:

1. **Given** 部署完成，**When** 檢視 repo 與映像內容，**Then** 找不到任何真實 client secret / 簽章金鑰。

---

### Edge Cases

- **pod 重新排程到不同節點**：資料須跟著持久卷（本機單節點 k3s 下為 local-path，跨節點不在範圍）。
- **正式部署金鑰防呆**：標記為正式環境時，若簽章金鑰仍為開發預設值，應拒絕啟動（feature 017 既有行為）。
- **反向代理 / 網域（使用者自理）**：經 TLS 終結的反向代理時，應用需據轉發標頭產生正確的 https 登入回呼；否則 Google 會因回呼網址不符而拒絕。本 feature 預留此設定，但網域/憑證/Ingress host 不在範圍。
- **本機 http 存取**：經 localhost 以 http 存取時，session cookie 不要求 Secure（開發模式設定）。
- **PDF 系統依賴**：容器映像須內含 PDF 渲染與中文字體所需的系統依賴，否則稽核報告下載不可用。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系統 MUST 提供單一容器映像，內含執行所需的全部依賴（含 PDF 渲染與中文字體），且**不依賴任何外部資料庫**。
- **FR-002**: 系統 MUST 提供可套用到 K8s 的部署資源：應用工作負載、對內服務、持久卷。
- **FR-003**: 配對紀錄與自訂範本 MUST 存於持久卷；工作負載 pod 重啟/重建後 MUST 完整保留。
- **FR-004**: 機密（OAuth client、簽章金鑰）MUST 以叢集 Secret 提供，來源為操作者本機既有設定檔；MUST NOT 出現在版本控制或容器映像中。
- **FR-005**: MUST 沿用現有 Google OAuth client id；本機存取路徑 MUST 與既有已註冊的登入回呼相容，使本機測試免改 Google 設定即可登入。
- **FR-006**: 非機密設定（環境模式、cookie 模式、登入網域白名單、連結效期）MUST 以可調整方式提供（不需重建映像即可改）。
- **FR-007**: 應用 MUST 能在反向代理後產生正確的登入回呼網址（為日後網域/TLS 預留）；網域、DNS、TLS 憑證、Ingress host 設定 MUST NOT 屬於本 feature（由使用者自理，僅提供可填的範例）。
- **FR-008**: 本 feature MUST NOT 改動 `src/matcher`（純打包與部署）。

### Key Entities

- **容器映像**：可執行的 matcher（Web）+ 全部執行期依賴。
- **應用工作負載**：在叢集中運行映像的部署單元。
- **持久卷**：存放 `data/`（配對紀錄、自訂範本）的儲存。
- **機密（Secret）**：OAuth client、簽章金鑰等敏感設定。
- **設定（非機密）**：環境模式、cookie/網域/效期等可調參數。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 操作者用本機 kubectl 套用部署資源後，**5 分鐘內**應用就緒、本機可開啟首頁。
- **SC-002**: 使用者從本機存取點用**現有 Google 帳號**登入成功，並完成一次配對、下載稽核報告。
- **SC-003**: 刪除工作負載 pod 並重建後，先前的配對紀錄與自訂範本**100% 保留**。
- **SC-004**: 版本控制追蹤的檔案與容器映像中，**0 個真實機密值**。
- **SC-005**: `src/matcher` **0 行改動**（變更僅限新增 Dockerfile、部署資源、文件）。

## Assumptions

- 本機已安裝 kubectl 且 context 指向可用叢集（現為 k3s），叢集具預設 StorageClass（k3s local-path）可動態供應持久卷。
- 本機存取以「轉發到 localhost 既有埠」的方式提供，以沿用現有 OAuth 已註冊的回呼。
- 操作者本機既有設定檔已含現用的 Google OAuth client id / secret；上正式網域前會把簽章金鑰換成真實亂碼。
- 升級採「清空舊資料」既有決議；持久卷只保證**往後**不遺失。
- 沿用「無 DB、檔案系統儲存」架構與現有環境變數設定介面。
- 網域、DNS、TLS 憑證、Ingress host 由使用者自理（本 feature 僅附可填的範例）。
