# Quickstart：部署 matcher 到 k3s（本機 kubectl）

> 前提：本機已裝 `docker`、`kubectl`（context 指向 `k3s-tew`）、`gh`（已登入、含 `write:packages`）。
> 本機 `.env` 已有現用的 `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`；本機測試 `MATCHER_INSECURE_COOKIE=1`。

> **重點**：(1) 部署在 namespace **`matcher`**；(2) 節點是 **amd64**，本機若為 Apple Silicon 必須用
> `docker buildx --platform linux/amd64`（否則 pod 會 `no match for platform`）。

## 1. Build（amd64）+ 推映像到 ghcr

```sh
gh auth token | docker login ghcr.io -u timcsy --password-stdin
SHA=$(git rev-parse --short HEAD)
docker buildx build --platform linux/amd64 --provenance=false \
  -t ghcr.io/timcsy/matcher:$SHA -t ghcr.io/timcsy/matcher:latest --push .
```

> 首次推送後，到 GitHub 把該 package 設為 **public**（container package 可見性只能在網頁設：
> Package → Settings → Danger Zone → Change visibility），cluster 才能免帳密 pull。

## 2. 建 namespace + 灌機密（值來自本機 .env，不入庫）

```sh
kubectl apply -f deploy/k8s/namespace.yaml
kubectl create secret generic matcher-secrets -n matcher \
  --from-env-file=.env --dry-run=client -o yaml | kubectl apply -f -
```

## 3. 部署

```sh
# deployment.yaml 內 image tag 設為步驟 1 的 $SHA（manifests 已含 namespace: matcher）
kubectl apply -f deploy/k8s/pvc.yaml \
               -f deploy/k8s/service.yaml \
               -f deploy/k8s/deployment.yaml
kubectl rollout status deploy/matcher -n matcher --timeout=300s
```

## 4. 存取 + 登入（沿用現有 OAuth 回呼）

```sh
kubectl port-forward -n matcher svc/matcher 8765:8765
# 瀏覽器開 http://localhost:8765 → 用現有 Google 帳號登入
```

## 驗收（對應 Success Criteria）

- **SC-001**：`kubectl rollout status` 5 分鐘內 Ready；`curl -sf http://localhost:8765/login` 回 200。
- **SC-002**：瀏覽器 `http://localhost:8765` Google 登入成功 → 跑一次配對 → 下載稽核 PDF（驗證容器內 WeasyPrint/CJK 正常）。
- **SC-003（持久化）**：
  ```sh
  # 跑一筆配對 + 建一個自訂範本後：
  kubectl delete pod -n matcher -l app=matcher        # 觸發重建
  kubectl rollout status deploy/matcher -n matcher
  # 重新 port-forward，確認「過去紀錄」與該自訂範本仍在
  ```
- **SC-004**：`git grep -nIE 'GOCSPX-|gho_'`（追蹤檔）無結果；Secret 不在 repo。
- **SC-005**：`git diff main -- src/matcher` 為空。

## 之後上正式網域（使用者自理，非本 feature）

1. 在 `.env` 把 `SESSION_SECRET` 換成真實亂碼、設 `MATCHER_ENV=production`、移除 `MATCHER_INSECURE_COOKIE`，重灌 Secret。
2. 在 Google OAuth client 新增 `https://<你的網域>/auth/callback` 回呼。
3. 填 `deploy/k8s/ingress.example.yaml` 的網域與 TLS，套用。
4. app 已帶 `--proxy-headers`，會據轉發標頭產生 `https://` 回呼。

## 疑難排解

- **`no match for platform`**：映像架構與節點不符——用 `docker buildx --platform linux/amd64 --push` 重 build（節點是 amd64）。
- **pod CrashLoop / 起不來**：`kubectl logs -n matcher deploy/matcher`；若提示 SESSION_SECRET → 檢查是否誤設 `MATCHER_ENV=production` 但用了預設 secret。
- **登入回 callback 失敗**：確認用 `localhost:8765`（非其他埠/IP），且 Google client 有註冊 `http://localhost:8765/auth/callback`。
- **PDF 503 / 中文變空白**：映像缺系統依賴或 CJK 字體 → 檢查 Dockerfile apt 清單。
- **映像 pull 不到**：ghcr package 未設 public，或 tag 不符。
