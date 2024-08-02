package vault

import (
	"bytes"
	"encoding/json"
	"io/ioutil"
	"log"
	"net/http"

	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

// InitResponse holds a Vault init response.
type InitResponse struct {
	Keys       []string `json:"keys"`
	KeysBase64 []string `json:"keys_base64"`
	RootToken  string   `json:"root_token"`
}

type InitRequest struct {
	RecoveryShares    int `json:"recovery_shares"`
	RecoveryThreshold int `json:"recovery_threshold"`
	StoredShares      int `json:"stored_shares"`
}

func (v *HashicorpVault) VaultInit(ctx *pulumi.Context, opts ...pulumi.ResourceOption) (InitResponse, error) {
	v.Url.ApplyT(func(url *string) (InitResponse, error) {
		initRequest := InitRequest{
			RecoveryShares:    5,
			RecoveryThreshold: 3,
			StoredShares:      5,
		}

		initRequestData, err := json.Marshal(&initRequest)
		if err != nil {
			log.Println(err)
			return InitResponse{}, nil
		}

		r := bytes.NewReader(initRequestData)
		request, err := http.NewRequest("POST", *url+"/v1/sys/init", r)
		if err != nil {
			log.Println(err)
			return InitResponse{}, nil
		}

		httpClient := http.Client{}

		response, err := httpClient.Do(request)
		if err != nil {
			log.Println(err)
			return InitResponse{}, nil
		}
		defer response.Body.Close()

		initRequestResponseBody, err := ioutil.ReadAll(response.Body)
		if err != nil {
			log.Println(err)
			return InitResponse{}, nil
		}

		if response.StatusCode != 200 {
			log.Printf("init: non 200 status code: %d\n", response.StatusCode)
			log.Printf("debug: %s\n", initRequestResponseBody)
			return InitResponse{}, nil
		}

		var initResponse InitResponse

		if err := json.Unmarshal(initRequestResponseBody, &initResponse); err != nil {
			log.Println(err)
			return InitResponse{}, nil
		}

		log.Println("Initialization complete.\n%v\n", initResponse)
		return initResponse, nil
	})
	return InitResponse{}, nil
}
