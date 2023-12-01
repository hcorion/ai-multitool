python -V
tsc --version
sass --version

try {
    # Start the TypeScript compiler in watch mode as a background job
    $tsJob = Start-Job -ScriptBlock {
        tsc --watch --preserveWatchOutput
    }

    # Start the Sass compiler in watch mode as a background job
    $sassJob = Start-Job -ScriptBlock {
        sass --watch static/sass:static/css
    }

    # Start the Python flask app in watch mode as a background job
    $pyJob = Start-Job -ScriptBlock {
        python app.py
    }

    Write-Host "Press Ctrl+C to stop..."

    # Initialize variables to keep track of the last line processed
    $lastTsLine = 0
    $lastSassLine = 0
    $lastPyLine = 0

    # Function to receive and display new job output
    function Update-NewOutput {
        param (
            [Parameter(Mandatory = $true)]
            [System.Management.Automation.Job]$Job,
    
            [ref]$LastLine
        )
    
        $output = Receive-Job -Job $Job
        if ($output -and $output.Count -gt $LastLine.Value) {
            $newOutput = $output[$LastLine.Value..($output.Count - 1)]
            $LastLine.Value = $output.Count
            return $newOutput
        }
    }

    # Monitor jobs and display their output
    do {
        if (Get-Job -State Stopped) {
            break
        }

        Update-NewOutput -Job $tsJob -LastLine ([ref]$lastTsLine) | Write-Host
        Update-NewOutput -Job $sassJob -LastLine ([ref]$lastSassLine) | Write-Host
        Update-NewOutput -Job $pyJob -LastLine ([ref]$lastPyLine) | Write-Host

        Start-Sleep -Seconds 2
    } while ($true)

} catch {
    Write-Error $Error[0]
} finally {
    # Stop all jobs and remove them
    Write-Host "Ctrl+C detected, stopping jobs..."
    Get-Job | Stop-Job
    Get-Job | Remove-Job
    Write-Host "All jobs have been stopped and removed."
}