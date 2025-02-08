const { Connection, PublicKey } = require('@solana/web3.js');
const axios = require('axios').default;

// Constants
const INPUT_MINT = 'So11111111111111111111111111111111111111112'; // SOL
const OUTPUT_MINT = '6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump'; // VINE
const AMOUNT = 5 * 1e9; // 5 SOL in lamports
const SLIPPAGE_BPS = 250; // 2.5%
const JUPITER_V6_ENDPOINT = 'https://quote-api.jup.ag/v6';

// Configure axios defaults
axios.defaults.headers.common['Content-Type'] = 'application/json';
axios.defaults.headers.common['Accept'] = 'application/json';

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
        
        const quoteResponse = await axios.get(`${JUPITER_V6_ENDPOINT}/quote`, {
            params: {
                inputMint: INPUT_MINT,
                outputMint: OUTPUT_MINT,
                amount: AMOUNT.toString(),
                slippageBps: SLIPPAGE_BPS.toString()
            }
        });
        
        const quote = quoteResponse.data;
        
        if (!quote || !quote.outAmount) {
            throw new Error('Invalid quote response');
        }
        
        console.log('\n✅ 获取报价成功 | Quote received successfully');
        console.log(`预计输出 | Expected output: ${quote.outAmount} VINE`);
        console.log(`价格影响 | Price impact: ${quote.priceImpactPct}%`);
        
        // Step 2: Get swap instructions
        console.log('\n🔄 获取交易指令中... | Getting swap instructions...');
        
        // Extract only the necessary fields from the quote for the swap request
        const swapRequest = {
            quoteResponse: {
                inputMint: quote.inputMint,
                outputMint: quote.outputMint,
                inAmount: quote.inAmount,
                outAmount: quote.outAmount,
                otherAmountThreshold: quote.otherAmountThreshold,
                swapMode: quote.swapMode,
                slippageBps: quote.slippageBps,
                platformFee: quote.platformFee,
                priceImpactPct: quote.priceImpactPct,
                routePlan: quote.routePlan,
                contextSlot: quote.contextSlot
            },
            userPublicKey: walletKey,
            wrapUnwrapSOL: true,
            useSharedAccounts: true,
            feeAccount: null,
            computeUnitPriceMicroLamports: null,
            asLegacyTransaction: false
        };
        
        const swapResponse = await axios.post(`${JUPITER_V6_ENDPOINT}/swap`, swapRequest);
        const swapResult = swapResponse.data;
        
        if (!swapResult || !swapResult.swapTransaction) {
            throw new Error('Invalid swap response');
        }
        
        // Step 3: Execute swap
        console.log('\n🔄 执行交易中... | Executing swap...');
        const executeResponse = await axios.post(`${JUPITER_V6_ENDPOINT}/swap/execute`, {
            swapTransaction: swapResult.swapTransaction,
            userPublicKey: walletKey
        });
        
        const executeResult = executeResponse.data;
        
        if (!executeResult || !executeResult.txid) {
            throw new Error('Invalid execute response');
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
        if (error.response) {
            console.error(JSON.stringify({
                success: false,
                error: error.response.data?.error || error.message,
                status: error.response.status,
                data: error.response.data,
                request: {
                    url: error.config?.url,
                    method: error.config?.method,
                    data: JSON.parse(error.config?.data || '{}'),
                    params: error.config?.params
                }
            }, null, 2));
        } else {
            console.error(JSON.stringify({
                success: false,
                error: error.message,
                stack: error.stack
            }, null, 2));
        }
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
