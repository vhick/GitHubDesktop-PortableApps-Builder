/**
 * Application-specific source adapter loaded FIRST by main.ts.
 * The compiled launcher supplies GHD_PORTABLE_ROOT pointing at <Portable>\\Data.
 * No host-level environment/registry modifications occur here.
 */
import { app } from 'electron'
import * as Path from 'path'
import { mkdirSync } from 'fs'

const portableData = process.env.GHD_PORTABLE_ROOT
if (portableData) {
  const userData = Path.join(portableData, 'Profile')
  const browserData = Path.join(userData, 'Chromium')
  const logDir = Path.join(userData, 'logs')
  for (const dir of [userData, browserData, logDir]) {
    mkdirSync(dir, { recursive: true })
  }
  // Electron native paths MUST be set before the ready event and before other app imports.
  app.setPath('userData', userData)
  app.setPath('sessionData', browserData)
  app.setAppLogsPath(logDir)
  // Distinct portable AUMID. This is NOT an installed app's AUMID/CLSID.
  if (process.platform === 'win32') {
    app.setAppUserModelId('io.github.vhick.GitHubDesktopPortable')
  }
}
