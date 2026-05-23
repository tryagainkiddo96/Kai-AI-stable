<#
Windows PowerShell helper: securely set HF_API_KEY for your Kai session.
This writes the key to the current user's environment (session-wide).
Usage: .\scripts\set_hf_api_key.ps1
The script will prompt for the key without echoing it back.
> Important: Do not share your API key in public channels or code.
"#>
param()

$secure = Read-Host -Prompt 'Enter HF API Key' -AsSecureString
try {
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
} catch {
    Write-Error 'Failed to read the API key securely.'
    exit 1
}
[System.Environment]::SetEnvironmentVariable('HF_API_KEY', $plain, 'User')
Write-Host 'HF_API_KEY set for current user session. You may need to restart shells to pick up the new value.'
