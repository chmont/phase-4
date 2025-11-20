Write-Host "Starting central"

Set-Location .\central
docker compose down

Set-Location ..

$letters = 97 .. 100
$folder_prefix = "edge-"

foreach ($letter in $letters)
{
    $edge_path = $folder_prefix + [char] $letter
    
    Set-Location .\$edge_path 
    Write-Host "Now Stopping container:" $edge_path
    docker compose down
    Set-Location ..
}

Write-Host "Stopped all Containers"

