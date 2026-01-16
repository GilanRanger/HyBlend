const puppeteer = require('puppeteer-core');
const { exec } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const config = yaml.load(fs.readFileSync(path.join(__dirname, 'pipeline_configuration.yml'), 'utf8'));
const BLOCKBENCH_PATH = config.paths.blockbench;

let browser = null;
let blockbenchProcess = null;

async function initBrowser() {
    blockbenchProcess = exec(`"${BLOCKBENCH_PATH}" --remote-debugging-port=9222`);
    await new Promise(resolve => setTimeout(resolve, 8000));
    
    browser = await puppeteer.connect({
        browserURL: 'http://localhost:9222',
        defaultViewport: null
    });
    
    const page = (await browser.pages())[0];
    await page.waitForFunction(() => window.Codecs?.blockymodel !== undefined, { timeout: 30000 });
}

async function getPage() {
    return (await browser.pages())[0];
}

function findTextureFile(modelPath) {
    let currentDir = path.dirname(modelPath);
    
    while (currentDir) {
        const pngFiles = fs.readdirSync(currentDir).filter(f => f.endsWith('.png'));
        if (pngFiles.length > 0) {
            return path.join(currentDir, pngFiles[0]);
        }
        
        const parentDir = path.dirname(currentDir);
        if (parentDir === currentDir) break;
        currentDir = parentDir;
    }
    
    return null;
}

async function exportModel(blockymodelPath, outputGltfPath) {
    const page = await getPage();
    const modelText = fs.readFileSync(blockymodelPath, 'utf8');
    const texturePath = findTextureFile(blockymodelPath);

    const result = await page.evaluate(async (modelText, modelPath, texturePath) => {
        Formats.hytale_character.new();
        
        const originalShowMessageBox = Blockbench.showMessageBox;
        Blockbench.showMessageBox = function(options, callback) {
            if (options.title === 'Import Textures') {
                callback(2);
                return;
            }
            return originalShowMessageBox.call(this, options, callback);
        };
        
        Codecs.blockymodel.parse(JSON.parse(modelText), modelPath);
        Blockbench.showMessageBox = originalShowMessageBox;
        
        if (Project.textures.length === 0 && texturePath) {
            await new Promise((resolve) => {
                let texture = new Texture().fromPath(texturePath).add(false, true);
                texture.load(() => {
                    texture.use_as_default = true;
                    Cube.all.forEach(cube => {
                        for (let fkey in cube.faces) {
                            if (cube.faces[fkey].texture === null) {
                                cube.faces[fkey].texture = texture.uuid;
                            }
                        }
                    });
                    Canvas.updateAllFaces();
                    resolve();
                });
            });
        }
        
        await new Promise(resolve => setTimeout(resolve, 500));
        
        const gltfResult = await Codecs.gltf.compile({
            armature: true,
            embed_textures: true,
            animations: true
        });
        
        Project.close();
        return gltfResult;
    }, modelText, blockymodelPath, texturePath);

    if (typeof result === 'string') {
        fs.writeFileSync(outputGltfPath, result);
    } else {
        fs.writeFileSync(outputGltfPath, JSON.stringify(result, null, 2));
    }
    
    return true;
}

const server = http.createServer(async (req, res) => {
    if (req.method === 'GET' && req.url === '/health') {
        res.writeHead(200);
        res.end(JSON.stringify({ status: 'ready' }));
    } else if (req.method === 'POST' && req.url === '/export') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            try {
                const { input, output } = JSON.parse(body);
                await exportModel(input, output);
                res.writeHead(200);
                res.end(JSON.stringify({ success: true }));
            } catch (error) {
                res.writeHead(500);
                res.end(JSON.stringify({ error: error.message }));
            }
        });
    } else if (req.url === '/shutdown') {
        res.writeHead(200);
        res.end('Shutting down');
        if (browser) await browser.disconnect();
        if (blockbenchProcess) blockbenchProcess.kill();
        process.exit(0);
    } else {
        res.writeHead(404);
        res.end();
    }
});

initBrowser()
    .then(() => server.listen(3002))
    .catch(err => {
        console.error('Startup failed:', err);
        process.exit(1);
    });