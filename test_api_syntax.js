const fs = require('fs');
const path = require('path');

const apiContent = fs.readFileSync(path.join(__dirname, 'frontend/services/api.ts'), 'utf8');

// Try to parse with TypeScript compiler (simplified)
// Just check for obvious syntax errors like unmatched braces
let braceCount = 0;
let parenCount = 0;
let bracketCount = 0;

for (let i = 0; i < apiContent.length; i++) {
    const char = apiContent[i];
    if (char === '{') braceCount++;
    else if (char === '}') braceCount--;
    else if (char === '(') parenCount++;
    else if (char === ')') parenCount--;
    else if (char === '[') bracketCount++;
    else if (char === ']') bracketCount--;
    
    if (braceCount < 0 || parenCount < 0 || bracketCount < 0) {
        console.error(`Mismatched closing at position ${i}: ${apiContent.substring(i-20, i+20)}`);
        break;
    }
}

console.log(`Braces: ${braceCount}, Parens: ${parenCount}, Brackets: ${bracketCount}`);

// Check for obvious export syntax errors
const lines = apiContent.split('\n');
let inMultiLineComment = false;
for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    // Handle multi-line comments
    if (line.includes('/*') && !line.includes('*/')) {
        inMultiLineComment = true;
    }
    if (line.includes('*/')) {
        inMultiLineComment = false;
    }
    
    if (inMultiLineComment) continue;
    
    // Check for export async function without proper closing
    if (line.includes('export async function') && !line.includes('{')) {
        console.log(`Warning: export async function without opening brace at line ${i+1}: ${line}`);
    }
}

// Check last few lines for stray characters
console.log('\nLast 20 lines:');
lines.slice(-20).forEach((line, idx) => {
    console.log(`${lines.length - 20 + idx + 1}: ${line}`);
});