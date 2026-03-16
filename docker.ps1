param(
    [Parameter(Position = 0)]
    [ValidateSet("dev-up", "dev-build", "dev-down", "dev-logs", "prod-up", "prod-build", "prod-down", "prod-logs")]
    [string]$Command = "dev-up"
)

$ErrorActionPreference = "Stop"

function Invoke-Compose {
    param(
        [string[]]$Args
    )

    Write-Host "Running: docker compose $($Args -join ' ')" -ForegroundColor Cyan
    & docker compose @Args
}

function Invoke-ComposeProd {
    param(
        [string[]]$Args
    )

    $prodArgs = @("-f", "docker-compose.prod.yml") + $Args
    Write-Host "Running: docker compose $($prodArgs -join ' ')" -ForegroundColor Yellow
    & docker compose @prodArgs
}

switch ($Command) {
    "dev-up" {
        Invoke-Compose -Args @("up")
    }
    "dev-build" {
        Invoke-Compose -Args @("up", "--build")
    }
    "dev-down" {
        Invoke-Compose -Args @("down")
    }
    "dev-logs" {
        Invoke-Compose -Args @("logs", "-f")
    }
    "prod-up" {
        Invoke-ComposeProd -Args @("up", "-d")
    }
    "prod-build" {
        Invoke-ComposeProd -Args @("up", "--build", "-d")
    }
    "prod-down" {
        Invoke-ComposeProd -Args @("down")
    }
    "prod-logs" {
        Invoke-ComposeProd -Args @("logs", "-f")
    }
}
