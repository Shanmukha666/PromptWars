import puppeteer from 'puppeteer-core'
import path from 'path'

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const OUTPUT_DIR = 'C:\\Users\\SIREESHA DASARI\\.gemini\\antigravity\\brain\\92b8e159-2b86-4b4b-8921-4c5b1f5519c3'

const stages = ['overview', 'profile', 'reports', 'structured', 'review', 'timeline', 'processing']

async function run() {
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  })

  const viewports = [
    { name: '1440', width: 1440, height: 900 },
    { name: '1024', width: 1024, height: 768 },
    { name: '390', width: 390, height: 844, isMobile: true }
  ]

  const page = await browser.newPage()

  for (const vp of viewports) {
    await page.setViewport({ width: vp.width, height: vp.height, isMobile: vp.isMobile || false })
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle0', timeout: 15000 })
    await new Promise(r => setTimeout(r, 1000))

    // Select the first real patient from header dropdown
    try {
      const select = await page.$('#header-patient-select')
      if (select) {
        const options = await page.$$eval('#header-patient-select option', opts => 
          opts.map(o => o.value).filter(v => v && !v.startsWith('__') && v !== '')
        )
        if (options.length > 0) {
          await page.select('#header-patient-select', options[0])
          await new Promise(r => setTimeout(r, 800))
        }
      }
    } catch (e) {
      console.log('Error selecting patient:', e.message)
    }

    // Capture each stage
    for (const stage of stages) {
      try {
        if (stage !== 'overview') {
          // If sidebar is hidden (mobile/tablet), trigger open or click directly via JS
          await page.evaluate((stg) => {
            const btn = document.querySelector(`button[data-stage="${stg}"]`)
            if (btn) {
              btn.click()
            }
          }, stage)
          await new Promise(r => setTimeout(r, 800))
        }

        const outPath = path.join(OUTPUT_DIR, `screen_${vp.name}_${stage}.png`)
        await page.screenshot({ path: outPath, fullPage: false })
        console.log(`Captured: screen_${vp.name}_${stage}.png`)
      } catch (err) {
        console.log(`Failed on ${stage} @ ${vp.name}:`, err.message)
      }
    }
  }

  await browser.close()
}

run().catch(err => {
  console.error(err)
  process.exit(1)
})
