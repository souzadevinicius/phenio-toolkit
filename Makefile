UPHENO_DIR = upheno-release
FILES = upheno_species_lexical.csv upheno_mapping_logical.csv upheno_all_with_relations.owl

.PHONY: download

download: $(patsubst %, $(UPHENO_DIR)/%, $(FILES))


$(UPHENO_DIR)/%:
	wget https://bbop-ontologies.s3.amazonaws.com/upheno/current/upheno-release/all/$* -O $@