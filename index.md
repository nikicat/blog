## How to create lnd node ready for accepting payments

# Install lnd
```
yay -S lnd
```

# Configure
```
mkdir ~/.lnd
cat <<EOF
bitcoin.active=true
bitcoin.mainnet=true
bitcoin.node=neutrino
feeurl=https://nodes.lightning.computer/fees/v1/btc-fee-estimates.json
no-rest-tls=true
EOF > ~/.lnd/lnd.conf
```

# Create wallet
```
lnd &
lncli create
# pass password here and save seed phrase afterwards
kill %1
```

# Setup autounlock and start lnd
```
echo "<password-for-the-wallet>" > ~/.lnd/wallet.password
echo "wallet-unlock-password-file=~/.lnd/wallet.password" >> ~/.lnd/lnd.conf
lnd &
```

# Obtain inbound liquidity
 - go to https://lnbig.com
 - initiate the payment
 - provide node id `lncli getinfo | jq -r .identity_pubkey`
 - use NodeID@Host:Port to connect to the node `lncli connect <addr>`
 - wait for on-chain confirmation
