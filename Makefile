all: package

package: requests lambda-aws-billing-notifications.zip
	
requests:
	pip install requests -t .

lambda-aws-billing-notifications.zip: requests lambda_function.py config.json
	rm -rf lambda-aws-billing-notifications.zip
	zip -r --exclude=".git*" \
		--exclude="Makefile" \
		--exclude="config.json.example" \
		--exclude="README.md" lambda-aws-billing-notifications.zip .

.PHONY: all package
