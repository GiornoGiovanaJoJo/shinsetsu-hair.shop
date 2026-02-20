const { NodeSSH } = require('node-ssh');
const ssh = new NodeSSH();
const path = require('path');

const config = {
    host: '195.161.69.221',
    port: 22,
    username: 'root',
    password: 'Nikitoso02-'
};

const localPath = __dirname;
const remotePath = '/root/shinsetsu-hair';

async function deployFront() {
    try {
        console.log('Connecting to SSH...');
        await ssh.connect(config);
        console.log('Connected!');

        console.log('Uploading frontend files...');

        await ssh.putFiles([
            { local: path.join(localPath, 'index.html'), remote: `${remotePath}/index.html` },
            { local: path.join(localPath, 'styles.css'), remote: `${remotePath}/styles.css` },
            { local: path.join(localPath, 'script.js'), remote: `${remotePath}/script.js` }
        ]);
        console.log('Main files uploaded.');

        console.log('Uploading templates directory...');
        await ssh.putDirectory(path.join(localPath, 'templates'), `${remotePath}/templates`, {
            recursive: true,
            concurrency: 10,
            validate: (itemPath) => path.basename(itemPath).substr(0, 1) !== '.'
        });

        console.log('Uploading fonts directory...');
        await ssh.putDirectory(path.join(localPath, 'fonts'), `${remotePath}/fonts`, {
            recursive: true,
            concurrency: 10
        });

        console.log('Success! Frontend files have been updated.');
        ssh.dispose();
    } catch (error) {
        console.error('Update Failed:', error);
        ssh.dispose();
    }
}

deployFront();
