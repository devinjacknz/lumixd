const { Jupiter } = require('@jup-ag/api');
const { Connection, PublicKey } = require('@solana/web3.js');

// Constants
const INPUT_MINT = 'So11111111111111111111111111111111111111112'; // SOL
const OUTPUT_MINT = '6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump'; // VINE
const AMOUNT = 5 * 1e9; // 5 SOL in lamports
const SLIPPAGE_BPS = 250; // 2.5%

async function executeSwap(walletKey) {
    try {
        console.log('\n🔍 获取连接中... | Getting connection...');
        const connection = new Connection(process.env.RPC_ENDPOINT || 'https://api.mainnet-beta.solana.com');
        
        // Initialize Jupiter
        console.log('\n🔄 初始化Jupiter... | Initializing Jupiter...');
        const jupiter = await Jupiter.load({
            connection,
            cluster: 'mainnet-beta',
            user: new PublicKey(walletKey),
            wrapUnwrapSOL: true,
            slippageBps: SLIPPAGE_BPS,
            maxAccounts: 54
        });
        
        // Get routes
        console.log('\n🔍 获取交易路径... | Getting routes...');
        console.log(`输入代币 | Input token: SOL (${INPUT_MINT})`);
        console.log(`输出代币 | Output token: VINE (${OUTPUT_MINT})`);
        console.log(`数量 | Amount: 5 SOL`);
        console.log(`滑点 | Slippage: ${SLIPPAGE_BPS/100}%`);
        
        const routes = await jupiter.computeRoutes({
            inputMint: new PublicKey(INPUT_MINT),
            outputMint: new PublicKey(OUTPUT_MINT),
            amount: AMOUNT,
            slippageBps: SLIPPAGE_BPS,
            onlyDirectRoutes: false,
            filterTopNResult: 1,
            maxAccounts: 54
        });
        
        if (!routes.routesInfos.length) {
            throw new Error('No routes found');
        }
        
        // Get best route
        const bestRoute = routes.routesInfos[0];
        
        console.log('\n✅ 获取路径成功 | Route received successfully');
        console.log(`预计输出 | Expected output: ${bestRoute.outAmount} VINE`);
        console.log(`价格影响 | Price impact: ${bestRoute.priceImpactPct}%`);
        
        // Execute swap
        console.log('\n🔄 执行交易中... | Executing swap...');
        const { execute } = await jupiter.exchange({
            routeInfo: bestRoute,
            userPublicKey: new PublicKey(walletKey),
            wrapUnwrapSOL: true,
            computeUnitPriceMicroLamports: null,
            asLegacyTransaction: false,
            useSharedAccounts: true,
            dynamicComputeUnitLimit: true
        });
        
        const result = await execute();
        
        if (!result || !result.signature) {
            throw new Error('Invalid swap result');
        }
        
        const signature = result.signature;
        console.log('\n✅ 交易成功 | Trade successful');
        console.log(`交易签名 | Transaction signature: ${signature}`);
        console.log(`查看交易 | View transaction: https://solscan.io/tx/${signature}`);
        
        // Verify transaction
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
            error: error.message,
            stack: error.stack
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
