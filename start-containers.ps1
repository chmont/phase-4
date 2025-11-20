Write-Host "Starting central"

Set-Location .\central
docker compose up -d

Set-Location ..

$letters = 97..100
$folder_prefix = "edge-"

foreach ($letter in $letters)
{
    $edge_path = $folder_prefix + [char] $letter
    
    Set-Location .\$edge_path 
    Write-Host "Now Starting container: " $edge_path
    docker compose up -d --build
    Set-Location ..
}

Write-Host "Started all Edge Containers"
