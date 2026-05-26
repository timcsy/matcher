# Feature Specification: 登入與資源歸屬

**Feature Branch**: `014-auth-ownership`
**Created**: 2026-05-26
**Status**: Draft
**Input**: 部署到公開網路前的隱私補強——Google OAuth 登入、資源綁擁有者、預設私有、範本可設公開、個別查詢連結改用不可猜的 token。

## Background / 動機

matcher 即將部署到**公開網路**。目前任何人開網址就能看到所有配對紀錄（含學生姓名與分發結果）、執行配對、建立範本。在公開網路上承載真實學生個資，這是不可接受的隱私風險。

兩個層面要處理：

1. **行政視角要登入保護**：列表、完整結果頁、建範本等「管理」操作，只有登入的擁有者能用。
2. **個別查詢連結的弱點**：當事人（家長、老師）沒有帳號，是透過連結看自己的結果。目前連結是 `/match/{id}/role/{role_id}`，而 role_id 可枚舉（T01、T02…）——一旦配對 id 外流，任何人可枚舉出全班結果。公開網路上這等於名單半公開。

本 feature 用 **Google OAuth 登入 + 資源綁擁有者 + 預設私有 + 個別連結改不可猜 token** 解決，且**不引入資料庫**（沿用檔案系統，僅在既有 JSON/YAML 加欄位）。

## User Scenarios & Testing

### User Story 1 - 行政登入後只看到自己的東西（Priority: P1）

身為學校行政，我用 Google 帳號登入後，列表與管理頁只顯示我自己建立的範本與配對紀錄；別人的我看不到、也不能用直接網址開啟。未登入時，管理頁一律導向登入。

**Why this priority**：這是隱私風險的核心解法。沒有它，公開網路部署不可行。

**Independent Test**：未登入訪問 `/matches`、`/match/{id}`（完整頁）、`/templates/new` → 導向登入；登入使用者 A 建立配對後，使用者 B 登入看不到 A 的紀錄，B 直接開 A 的 `/match/{id}` 被擋。

**Acceptance Scenarios**：

1. **Given** 未登入，**When** 訪問 `/matches`，**Then** 導向 Google 登入
2. **Given** A 已登入並建立一筆配對，**When** B 登入後看 `/matches`，**Then** 看不到 A 的那筆
3. **Given** A 的配對 id，**When** B（已登入）直接開 `/match/{A的id}`，**Then** 403 或「無權查看」
4. **Given** 已登入，**When** 完成 OAuth，**Then** 後續請求維持登入狀態（session cookie）

---

### User Story 2 - 當事人用 token 連結看自己結果，不需登入（Priority: P1）

身為被配對的當事人（家長、老師），我收到一條帶不可猜 token 的連結，打開就能看到「我自己」的配對結果與判定理由，不需要任何帳號；別人就算知道配對 id 也無法枚舉出其他人的結果。

**Why this priority**：這是產品的核心用途（把結果發給當事人），且修掉公開網路上的枚舉漏洞。與 US1 同等重要——少了它，要嘛家長看不到、要嘛個資外洩。

**Independent Test**：配對完成後，每位角色拿到 `/r/{32+ 位隨機 token}` 連結；未登入開啟正常顯示該角色結果；把連結的 token 換成別的角色的 role_id 或亂猜 → 找不到 / 403；舊式 `/match/{id}/role/{role_id}` 路徑不再可被匿名枚舉。

**Acceptance Scenarios**：

1. **Given** 一筆完成的配對，**When** 行政開啟結果頁，**Then** 每位角色都有一條帶 token 的個別連結可複製
2. **Given** 某角色的 token 連結，**When** 未登入者開啟，**Then** 正常顯示「該角色」的結果與理由
3. **Given** 已知配對 id 但無 token，**When** 嘗試用 role_id 枚舉，**Then** 無法取得任何人的結果
4. **Given** A 角色的 token，**When** 用它嘗試看 B 角色，**Then** 只會看到 A，看不到 B

---

### User Story 3 - 範本可設為公開供他人複用（Priority: P2）

身為範本作者，我可以把自己的範本設為「公開」，讓其他登入使用者看得到、可複製來用（公開的只是規則，不含學生資料）；預設為私有。

**Why this priority**：範本無個資，公開很安全，且能讓好範本被複用。但非隱私核心，列 P2。

**Independent Test**：A 建範本預設私有，B 登入看不到；A 設為公開後，B 看得到且可 Fork 複製；B 不能編輯 A 的範本（只能複製）。

**Acceptance Scenarios**：

1. **Given** A 建立的私有範本，**When** B 瀏覽範本列表，**Then** 看不到該範本
2. **Given** A 將範本設為公開，**When** B 瀏覽，**Then** 看得到並可「複製為自訂版本」
3. **Given** B 看到 A 的公開範本，**When** B 嘗試編輯，**Then** 不允許（只能複製）
4. 內建範本（teacher-class、study-group）對所有登入者皆可見、可複製

---

### Edge Cases

- **既有無擁有者的資料**：升級前的 `data/matches/*.json`、`data/templates/` 沒有擁有者欄位 → 需決定歸屬策略（見 Clarifications）
- **公開網路安全**：表單需 CSRF 防護；session cookie 需 Secure/HttpOnly/SameSite；假設前面有反向代理終結 HTTPS
- **token 撞庫**：token 需足夠亂度（≥128 bit）讓暴力枚舉不可行
- **OAuth 失敗 / 取消授權**：使用者在 Google 取消 → 回到登入頁並顯示友善訊息
- **登出**：使用者能主動登出，清除 session
- **誰能登入**：公開網路上任何 Google 帳號都能登入嗎？（見 Clarifications）

## Requirements

### Functional Requirements

- **FR-001**：系統 MUST 提供 Google OAuth 登入；不實作本地密碼帳號
- **FR-002**：管理頁（`/matches`、完整結果頁 `/match/{id}`、`/match/new*`、`/templates/new`、`/templates/{id}/edit`、紀錄/範本相關操作）MUST 要求登入；未登入導向登入流程
- **FR-003**：每筆配對紀錄與每個自訂範本 MUST 記錄擁有者（登入者的 email）
- **FR-004**：列表頁 MUST 只顯示「當前登入者擁有的」資源（範本另含公開範本與內建範本）
- **FR-005**：存取非自己擁有且非公開的資源 MUST 回 403 / 無權查看
- **FR-006**：每位角色 MUST 有一條帶不可猜 token（≥128 bit 亂度）的個別查詢連結
- **FR-007**：token 個別連結 MUST 可被未登入者開啟，且只顯示對應該角色的資料
- **FR-008**：透過 token 連結 MUST 無法看到同一配對其他角色的資料；舊式可枚舉路徑 MUST 不再讓匿名者取得結果
- **FR-009**：自訂範本 MUST 支援「私有 / 公開」兩段可見性，預設私有
- **FR-010**：公開範本 MUST 可被其他登入者瀏覽與複製，但 MUST NOT 可被非擁有者編輯
- **FR-011**：所有改變狀態的表單（POST）MUST 有 CSRF 防護
- **FR-012**：session cookie MUST 設 Secure、HttpOnly、SameSite
- **FR-013**：使用者 MUST 能登出
- **FR-014**：核心 `src/matcher/{rules,filter,allocator,pipeline,audit,rng,roster,data_import,template_loader}` MUST 0 改動（auth 屬周邊整合，教訓 7）
- **FR-015**：MUST NOT 引入資料庫；擁有者與可見性以欄位存於既有 JSON/YAML
- **FR-016**：登入開放任何 Google 帳號（無白名單）；SHOULD 對 OAuth 與執行配對端點加基本 rate-limit 以降低濫用
- **FR-017**：升級時 MUST 清空既有 `data/matches/`、`data/templates/`（視為開發資料，不做遷移）

### Key Entities

- **使用者（User）**：以 Google email 識別；不另存密碼。session 記錄當前登入 email。
- **配對紀錄（MatchRecord）**：新增 `owner`（email）欄位；每個角色關聯一個 `token`。
- **範本（Template / 版本檔）**：新增 `owner`（email）與 `visibility`（private / public）欄位。
- **個別 token 連結**：token → (配對 id, 角色 id) 的對應，存於配對紀錄內。

## Success Criteria

### Measurable Outcomes

- **SC-001**：未登入訪問任一管理頁 → 100% 導向登入；個別 token 連結未登入仍可開
- **SC-002**：使用者只在列表看到自己的資源 + 公開範本 + 內建範本；跨使用者直接存取被擋（403）
- **SC-003**：個別 token 連結亂度 ≥128 bit；已知配對 id 無 token 時無法取得任何角色結果
- **SC-004**：範本可切私有/公開；公開範本他人可見可複製、不可編輯
- **SC-005**：全測試（含現有 352 + 本 feature 新增）綠
- **SC-006**：核心 `src/matcher/*`（非 web）git diff 為空
- **SC-007**：所有 POST 表單具 CSRF token；session cookie 具 Secure/HttpOnly/SameSite

## Assumptions

- 部署在公開網路，前面有反向代理終結 HTTPS（app 本身不處理 TLS 憑證）
- 沿用檔案系統儲存，不引入資料庫（與既有架構決策一致）
- Google OAuth client 憑證由維運者於 Google Cloud 建立並以環境變數提供（不寫死、不入 repo）
- 既有 CLI 路徑不受影響（登入是 Web 專屬；CLI 無帳號概念）
- 個別查詢連結改 token 後，舊式 `/match/{id}/role/{role_id}` 路徑對匿名者關閉（或要求登入且為擁有者）

## Clarifications（已解決）

1. **誰能登入？** → **開放註冊：任何 Google 帳號都能登入並建立資源。**
   - 影響：公開網路上陌生人可使用，因此 FR-011（CSRF）與基本 rate-limit（OAuth、執行配對）更形重要，以降低濫用 / 塞滿磁碟風險。維運層面 SHOULD 監控 `data/` 用量。
2. **私有給誰？** → **純個人私有。** 每個使用者只看得到自己建的（範本另含公開範本與內建範本）。不做「同網域互看」。
3. **既有無主資料如何處理？** → **直接清掉。** 現有 `data/matches/`、`data/templates/` 視為開發/測試資料，升級時清空；不需遷移邏輯。

> 三題已定，spec 可進入 `/speckit.plan`。
