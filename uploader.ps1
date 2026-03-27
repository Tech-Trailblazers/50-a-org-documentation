# Save this as git-auto-update.ps1
# This script will run forever, committing and pushing every 10 minutes

while ($true) {
    Write-Host "Starting git cycle at $(Get-Date)" -ForegroundColor Cyan

    # Pull the latest changes from the remote
    git pull

    # Stage all changes
    git add .

    # Commit changes with a message
    git commit -m "Automated commit at $(Get-Date)"

    # Push to the current branch's remote
    git push

    Write-Host "Cycle completed. Waiting 30 minute..." -ForegroundColor Green
    Start-Sleep -Seconds 1800  # 1800 seconds = 30 minutes
}