const { Connection, PublicKey } = require('@solana/web3.js');
const { Jupiter } = require('@jup-ag/core');

// Constants
const INPUT_MINT = 'So11111111111111111111111111111111111111112'; // SOL
const OUTPUT_MINT = '6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump'; // VINE
const AMOUNT = 5 * 1e9; // 5 SOL in lamports
const SLIPPAGE_BPS = 250; // 2.5%

async function executeSwap(walletKey) {
    try {
        // Setup connection
        const connection = new Connection('https://api.mainnet-beta.solana.com');
        
        // Initialize Jupiter
        const jupiter = await Jupiter.load({
            connection,
            cluster: 'mainnet-beta',
            user: new PublicKey(walletKey)
        });
        
        // Get routes
        const routes = await jupiter.computeRoutes({
            inputMint: new PublicKey(INPUT_MINT),
            outputMint: new PublicKey(OUTPUT_MINT),
            amount: AMOUNT,
            slippageBps: SLIPPAGE_BPS
        });
        
        if (!routes.routesInfos.length) {
            console.error('No routes found');
            process.exit(1);
        }
        
        // Get best route
        const bestRoute = routes.routesInfos[0];
        
        // Execute swap
        const { execute } = await jupiter.exchange({
            routeInfo: bestRoute
        });
        
        const result = await execute();
        
        // Log result
        console.log(JSON.stringify({
            success: true,
            signature: result.signature,
            inputAmount: bestRoute.inAmount,
            outputAmount: bestRoute.outAmount
        }));
        
    } catch (error) {
        console.error(JSON.stringify({
            success: false,
            error: error.message
        }));
        process.exit(1);
    }
}

// Get wallet key from command line args
const walletKey = process.argv[2];
if (!walletKey) {
    console.error('Wallet key required');
    process.exit(1);
}

executeSwap(walletKey);
