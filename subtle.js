/// Polyfill for (a small subset of) of the Web Crypto API in node

const crypto = require('crypto');

async function importKey(_, key) {
    return key;
}

async function decrypt({ iv }, key, buffer) {
    const decipher = crypto.createDecipheriv("aes-128-cbc", key, iv);
    const out = decipher.update(buffer);
    const final = decipher.final()
    return Buffer.concat([out, final]);
}

async function encrypt({ iv }, key, buffer) {
    const cipher = crypto.createCipheriv("aes-128-cbc", key, iv);
    const out = cipher.update(buffer);
    const final = cipher.final()
    return Buffer.concat([out, final]);
}

module.exports = { importKey, decrypt, encrypt }