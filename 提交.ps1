# git_auto_commit.ps1

# 获取计算机名和时间
$computerName = $env:COMPUTERNAME
$currentTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$COMMIT_MESSAGE = "自动提交 [$computerName] - $currentTime"

Write-Host "开始Git提交流程..."
Write-Host "提交信息: $COMMIT_MESSAGE"

# 执行Git流程
git status
git add .
git commit -m "$COMMIT_MESSAGE"
git push

Write-Host "? 所有更改已成功提交并推送！" -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
