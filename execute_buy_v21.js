const { Connection, PublicKey, Transaction } = require('@solana/web3.js');
const { QuoteApi, SwapApi } = require('@jup-ag/api');

// Constants
const INPUT_MINT = 'So11111111111111111111111111111111111111112'; // SOL
const OUTPUT_MINT = '6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump'; // VINE
const AMOUNT = 5 * 1e9; // 5 SOL in lamports
const SLIPPAGE_BPS = 250; // 2.5%

async function executeSwap(walletKey) {
    try {
        console.log('\n🔍 获取连接中... | Getting connection...');
        const connection = new Connection(process.env.RPC_ENDPOINT || 'https://api.mainnet-beta.solana.com');
        
        console.log('\n🔄 初始化Jupiter API... | Initializing Jupiter API...');
        const quoteApi = new QuoteApi();
        const swapApi = new SwapApi();
        
        console.log('\n🔍 计算交易路径... | Computing routes...');
        console.log(`输入代币 | Input token: SOL (${INPUT_MINT})`);
        console.log(`输出代币 | Output token: VINE (${OUTPUT_MINT})`);
        console.log(`数量 | Amount: 5 SOL`);
        console.log(`滑点 | Slippage: ${SLIPPAGE_BPS/100}%`);
        
        // Get quote
        const quote = await quoteApi.getQuote({
            inputMint: INPUT_MINT,
            outputMint: OUTPUT_MINT,
            amount: AMOUNT.toString(),
            slippageBps: SLIPPAGE_BPS,
            onlyDirectRoutes: false,
            asLegacyTransaction: false
        });
        
        if (!quote) {
            console.error('\n❌ 未找到交易路径 | No routes found');
            process.exit(1);
        }
        
        console.log('\n✅ 获取报价成功 | Quote received successfully');
        console.log(`预计输出 | Expected output: ${quote.outAmount} VINE`);
        console.log(`价格影响 | Price impact: ${quote.priceImpactPct}%`);
        
        // Get swap instructions
        console.log('\n🔄 获取交易指令中... | Getting swap instructions...');
        const swapResult = await swapApi.getSwap({
            quoteResponse: quote,
            userPublicKey: walletKey,
            wrapUnwrapSOL: true,
            computeUnitPriceMicroLamports: 50000
        });
        
        if (!swapResult) {
            console.error('\n❌ 获取交易指令失败 | Failed to get swap instructions');
            process.exit(1);
        }
        
        // Execute swap
        console.log('\n🔄 执行交易中... | Executing swap...');
        const { swapTransaction } = swapResult;
        
        const result = await swapApi.executeSwap({
            swapTransaction,
            userPublicKey: walletKey,
            computeUnitPriceMicroLamports: 50000
        });
        
        // Log result
        console.log('\n✅ 交易成功 | Trade successful');
        console.log(JSON.stringify({
            success: true,
            signature: result.txid,
            inputAmount: quote.inAmount,
            outputAmount: quote.outAmount
        }, null, 2));
        
        // Verify transaction
        console.log('\n🔍 验证交易中... | Verifying transaction...');
        const confirmation = await connection.confirmTransaction(result.txid);
        if (confirmation.value.err) {
            throw new Error(`Transaction failed: ${confirmation.value.err}`);
        }
        
        console.log('\n✅ 交易已确认 | Transaction confirmed');
        console.log(`查看交易 | View transaction: https://solscan.io/tx/${result.txid}`);
        
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
