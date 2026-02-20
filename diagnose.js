const { NodeSSH } = require('node-ssh');
const ssh = new NodeSSH();
const path = require('path');

const config = {
    host: '195.161.69.221',
    username: 'root',
    password: 'Nikitoso02-'
};

async function diagnose() {
    try {
        await ssh.connect(config);

        console.log('\n--- CHECK PUBLIC IP VS INTERFACE ---');
        let ifconfig = await ssh.execCommand('ip addr');
        console.log(ifconfig.stdout);

        let publicIp = await ssh.execCommand('curl -4 ifconfig.me');
        console.log('\nPublic IP (from external):', publicIp.stdout);

        console.log('\n--- CHECK HOSTNAME ---');
        let hostname = await ssh.execCommand('hostname -f');
        console.log(hostname.stdout);

        console.log('\n--- SEARCH FOR JINO CONFIGS ---');
        let jinoFiles = await ssh.execCommand('find /etc/nginx -name "*jino*"');
        console.log(jinoFiles.stdout);

        ssh.dispose();
    } catch (error) {
        console.error('Error:', error);
    }
}

diagnose();
