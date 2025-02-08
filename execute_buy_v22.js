const { Connection, PublicKey, Transaction, sendAndConfirmTransaction } = require('@solana/web3.js');
const fetch = require('node-fetch');

// Constants
const INPUT_MINT = 'So11111111111111111111111111111111111111112'; // SOL
const OUTPUT_MINT = '6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump'; // VINE
const AMOUNT = 5 * 1e9; // 5 SOL in lamports
const SLIPPAGE_BPS = 250; // 2.5%
const JUPITER_V6_ENDPOINT = 'https://quote-api.jup.ag/v6';

async function executeSwap(walletKey) {
    try {
        console.log('\n🔍 获取连接中... | Getting connection...');
        const connection = new Connection(process.env.RPC_ENDPOINT || 'https://api.mainnet-beta.solana.com');
        
        // Step 1: Get quote
        console.log('\n🔍 获取报价中... | Getting quote...');
        console.log(`输入代币 | Input token: SOL (${INPUT_MINT})`);
        console.log(`输出代币 | Output token: VINE (${OUTPUT_MINT})`);
        console.log(`数量 | Amount: 5 SOL`);
        console.log(`滑点 | Slippage: ${SLIPPAGE_BPS/100}%`);
        
        const quoteResponse = await fetch(`${JUPITER_V6_ENDPOINT}/quote?inputMint=${INPUT_MINT}&outputMint=${OUTPUT_MINT}&amount=${AMOUNT}&slippageBps=${SLIPPAGE_BPS}`);
        const quote = await quoteResponse.json();
        
        if (!quote || quote.error) {
            throw new Error(quote?.error || 'Failed to get quote');
        }
        
        console.log('\n✅ 获取报价成功 | Quote received successfully');
        console.log(`预计输出 | Expected output: ${quote.outAmount} VINE`);
        console.log(`价格影响 | Price impact: ${quote.priceImpactPct}%`);
        
        // Step 2: Get swap instructions
        console.log('\n🔄 获取交易指令中... | Getting swap instructions...');
        const swapRequestBody = {
            quoteResponse: quote,
            userPublicKey: walletKey,
            wrapUnwrapSOL: true,
            computeUnitPriceMicroLamports: 50000
        };
        
        const swapResponse = await fetch(`${JUPITER_V6_ENDPOINT}/swap`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(swapRequestBody)
        });
        
        const swapResult = await swapResponse.json();
        if (!swapResult || swapResult.error) {
            throw new Error(swapResult?.error || 'Failed to get swap instructions');
        }
        
        // Step 3: Execute swap
        console.log('\n🔄 执行交易中... | Executing swap...');
        const executeRequestBody = {
            swapTransaction: swapResult.swapTransaction,
            userPublicKey: walletKey,
            computeUnitPriceMicroLamports: 50000
        };
        
        const executeResponse = await fetch(`${JUPITER_V6_ENDPOINT}/swap/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(executeRequestBody)
        });
        
        const executeResult = await executeResponse.json();
        if (!executeResult || executeResult.error) {
            throw new Error(executeResult?.error || 'Failed to execute swap');
        }
        
        const signature = executeResult.txid;
        console.log('\n✅ 交易成功 | Trade successful');
        console.log(`交易签名 | Transaction signature: ${signature}`);
        console.log(`查看交易 | View transaction: https://solscan.io/tx/${signature}`);
        
        // Step 4: Verify transaction
        console.log('\n🔍 验证交易中... | Verifying transaction...');
        let retries = 3;
        while (retries > 0) {
            try {
                const confirmation = await connection.confirmTransaction(signature);
                if (!confirmation.value.err) {
                    console.log('\n✅ 交易已确认 | Transaction confirmed');
                    return signature;
                }
            } catch (e) {
                console.log(`\n⏳ 等待确认中... | Waiting for confirmation... (${retries} attempts left)`);
            }
            retries--;
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        
        throw new Error('Transaction verification failed');
        
    } catch (error) {
        console.error('\n❌ 交易失败 | Trade failed');
        console.error(JSON.stringify({
            success: false,
            error: error.message
        }, null, 2));
        process.exit(1);
    }
}

// Get wallet key from environment
const walletKey = process.env.WALLET_KEY;
if (!walletKey) {
    console.error('\n❌ 钱包密钥未设置 | Wallet key not set');
    process.exit(1);
}

executeSwap(walletKey);
