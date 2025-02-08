const { Connection, PublicKey, Keypair } = require('@solana/web3.js');
const bs58 = require('bs58');
const fetch = require('cross-fetch');

// Constants
const INPUT_MINT = 'So11111111111111111111111111111111111111112'; // SOL
const OUTPUT_MINT = '6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump'; // VINE
const AMOUNT = 5 * 1e9; // 5 SOL in lamports
const SLIPPAGE_BPS = 250; // 2.5%
const JUPITER_V6_ENDPOINT = 'https://quote-api.jup.ag/v6';

async function executeSwap(walletKey) {
    try {
        console.log('\n🔍 获取连接中... | Getting connection...');
        
        // Create keypair from private key
        const secretKey = Buffer.from(bs58.decode(walletKey));
        const keypair = Keypair.fromSecretKey(secretKey);
        
        // Step 1: Get quote
        console.log('\n🔍 获取报价中... | Getting quote...');
        console.log(`输入代币 | Input token: SOL (${INPUT_MINT})`);
        console.log(`输出代币 | Output token: VINE (${OUTPUT_MINT})`);
        console.log(`数量 | Amount: 5 SOL`);
        console.log(`滑点 | Slippage: ${SLIPPAGE_BPS/100}%`);
        
        const quoteResponse = await fetch(`${JUPITER_V6_ENDPOINT}/quote?inputMint=${INPUT_MINT}&outputMint=${OUTPUT_MINT}&amount=${AMOUNT}&slippageBps=${SLIPPAGE_BPS}&onlyDirectRoutes=false&asLegacyTransaction=false`);
        const quote = await quoteResponse.json();
        
        if (!quote || !quote.outAmount) {
            throw new Error('Invalid quote response');
        }
        
        console.log('\n✅ 获取报价成功 | Quote received successfully');
        console.log(`预计输出 | Expected output: ${quote.outAmount} VINE`);
        console.log(`价格影响 | Price impact: ${quote.priceImpactPct}%`);
        
        // Step 2: Get swap instructions
        console.log('\n🔄 获取交易指令中... | Getting swap instructions...');
        
        // Convert all numeric values to strings in the quote
        const stringifiedQuote = {
            ...quote,
            inAmount: quote.inAmount.toString(),
            outAmount: quote.outAmount.toString(),
            otherAmountThreshold: quote.otherAmountThreshold.toString(),
            swapMode: quote.swapMode,
            slippageBps: quote.slippageBps,
            platformFee: quote.platformFee,
            priceImpactPct: quote.priceImpactPct.toString(),
            routePlan: quote.routePlan.map(plan => ({
                ...plan,
                swapInfo: {
                    ...plan.swapInfo,
                    inAmount: plan.swapInfo.inAmount.toString(),
                    outAmount: plan.swapInfo.outAmount.toString(),
                    feeAmount: plan.swapInfo.feeAmount.toString()
                },
                percent: plan.percent
            })),
            contextSlot: quote.contextSlot,
            timeTaken: quote.timeTaken,
            swapUsdValue: quote.swapUsdValue.toString()
        };
        
        const swapRequestBody = {
            quoteResponse: stringifiedQuote,
            userPublicKey: keypair.publicKey.toString(),
            wrapUnwrapSOL: true,
            useSharedAccounts: true,
            computeUnitPriceMicroLamports: null,
            asLegacyTransaction: false,
            dynamicComputeUnitLimit: true,
            maxAccounts: 54
        };
        
        console.log('\nSwap Request:', JSON.stringify(swapRequestBody, null, 2));
        
        const swapInstructionsResponse = await fetch(`${JUPITER_V6_ENDPOINT}/swap-instructions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(swapRequestBody)
        });
        
        if (!swapInstructionsResponse.ok) {
            const errorText = await swapInstructionsResponse.text();
            throw new Error(`Swap instructions request failed: ${errorText}`);
        }
        
        const swapResult = await swapInstructionsResponse.json();
        
        if (!swapResult || !swapResult.swapTransaction) {
            console.error('Swap Instructions Response:', JSON.stringify(swapResult, null, 2));
            throw new Error('Invalid swap instructions response');
        }
        
        // Step 3: Execute swap
        console.log('\n🔄 执行交易中... | Executing swap...');
        const executeResponse = await fetch(`${JUPITER_V6_ENDPOINT}/swap/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                swapTransaction: swapResult.swapTransaction,
                userPublicKey: keypair.publicKey.toString(),
                dynamicComputeUnitLimit: true
            })
        });
        
        if (!executeResponse.ok) {
            const errorText = await executeResponse.text();
            throw new Error(`Swap execution request failed: ${errorText}`);
        }
        
        const executeResult = await executeResponse.json();
        
        if (!executeResult || !executeResult.txid) {
            console.error('Execute Response:', JSON.stringify(executeResult, null, 2));
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
                const response = await fetch(`https://api.mainnet-beta.solana.com`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        id: 1,
                        method: 'getTransaction',
                        params: [
                            signature,
                            {
                                commitment: 'confirmed',
                                maxSupportedTransactionVersion: 0
                            }
                        ]
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`Transaction verification request failed: ${await response.text()}`);
                }
                
                const result = await response.json();
                if (result.result && !result.result.meta.err) {
                    console.log('\n✅ 交易已确认 | Transaction confirmed');
                    return signature;
                }
            } catch (e) {
                console.log(`\n⏳ 等待确认中... | Waiting for confirmation... (${retries} attempts left)`);
                console.error(e);
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
                    params: error.config?.params,
                    headers: error.config?.headers
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
