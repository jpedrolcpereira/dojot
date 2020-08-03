#!/bin/bash

BASE_DIR=${BASE_DIR:-"/vernemq"}

. "${BASE_DIR}"/scripts_tls/_initVariables.sh

echo
echo "Retrieve CRL of trusted CA : ${certEjbcaApiUrl}/internal/api/v1/throw-away/ca/crl "

certCrl=$(curl  -X GET "${certEjbcaApiUrl}/internal/api/v1/throw-away/ca/crl?update=true" \
  -H "Content-Type:application/json" \
  -H "Accept:application/json" | jq '.crl' -r)

echo "${certCrl}" > "${certDir}"/tempcrl.crl

openssl crl -inform pem -in "${certDir}"/tempcrl.crl -out "${certDir}"/"${certCrlFile}"

chmod +x "${certDir}"/"${certCrlFile}"

rm  "${certDir}"/tempcrl.crl

