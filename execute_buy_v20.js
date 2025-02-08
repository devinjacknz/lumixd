const { Connection, PublicKey, Transaction, sendAndConfirmTransaction } = require('@solana/web3.js');
const { Jupiter } = require('@jup-ag/api');

// Constants
const INPUT_MINT = 'So11111111111111111111111111111111111111112'; // SOL
const OUTPUT_MINT = '6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump'; // VINE
const AMOUNT = 5 * 1e9; // 5 SOL in lamports
const SLIPPAGE_BPS = 250; // 2.5%

async function executeSwap(walletKey) {
    try {
        console.log('\n🔍 获取连接中... | Getting connection...');
        const connection = new Connection(process.env.RPC_ENDPOINT || 'https://api.mainnet-beta.solana.com');
        
        console.log('\n🔄 初始化Jupiter... | Initializing Jupiter...');
        const jupiter = await Jupiter.load({
            connection,
            cluster: 'mainnet-beta',
            user: new PublicKey(walletKey),
            wrapUnwrapSOL: true,
            platformFee: {
                feeBps: 5,
                feeAccounts: undefined
            }
        });
        
        console.log('\n🔍 计算交易路径... | Computing routes...');
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
            asLegacyTransaction: false,
            restrictIntermediateTokens: false
        });
        
        if (!routes.routesInfos.length) {
            console.error('\n❌ 未找到交易路径 | No routes found');
            process.exit(1);
        }
        
        // Get best route
        const bestRoute = routes.routesInfos[0];
        console.log('\n✅ 获取最佳路径 | Got best route');
        console.log(`预计输出 | Expected output: ${bestRoute.outAmount} VINE`);
        console.log(`价格影响 | Price impact: ${bestRoute.priceImpactPct}%`);
        
        // Execute swap
        console.log('\n🔄 执行交易中... | Executing swap...');
        const { execute } = await jupiter.exchange({
            routeInfo: bestRoute,
            userPublicKey: new PublicKey(walletKey),
            computeUnitPriceMicroLamports: 50000,
            asLegacyTransaction: false
        });
        
        const result = await execute();
        
        // Log result
        console.log('\n✅ 交易成功 | Trade successful');
        console.log(JSON.stringify({
            success: true,
            signature: result.signature,
            inputAmount: bestRoute.inAmount,
            outputAmount: bestRoute.outAmount
        }, null, 2));
        
        // Verify transaction
        console.log('\n🔍 验证交易中... | Verifying transaction...');
        const confirmation = await connection.confirmTransaction(result.signature);
        if (confirmation.value.err) {
            throw new Error(`Transaction failed: ${confirmation.value.err}`);
        }
        
        console.log('\n✅ 交易已确认 | Transaction confirmed');
        console.log(`查看交易 | View transaction: https://solscan.io/tx/${result.signature}`);
        
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
