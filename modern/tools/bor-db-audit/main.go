package main

// Read-only diagnosis against the official Bor v2.11.0 rawdb and Pebble APIs.
// This command neither starts a node nor changes pruning or consensus metadata.
import (
  "encoding/binary"
  "encoding/json"
  "fmt"
  "os"
  "time"
  "github.com/ethereum/go-ethereum/common"
  "github.com/ethereum/go-ethereum/core/rawdb"
  "github.com/ethereum/go-ethereum/crypto"
  "github.com/ethereum/go-ethereum/ethdb/pebble"
)
func main() {
 if len(os.Args)!=2 { panic("usage: bor-db-audit <chaindata>") }
 started:=time.Now()
 kv,err:=pebble.New(os.Args[1],256,256,"audit",true)
 if err!=nil {panic(err)}
 defer kv.Close()
 db:=rawdb.NewDatabase(kv)
 headHash:=rawdb.ReadHeadHeaderHash(db)
 headNumber,ok:=rawdb.ReadHeaderNumber(db,headHash);if !ok {panic("head header number missing")}
 head:=rawdb.ReadHeaderFromKvStore(db,headHash,headNumber);if head==nil {panic("head header missing")}
 start:=make([]byte,8);binary.BigEndian.PutUint64(start,1)
 it:=kv.NewIterator([]byte("h"),start)
 var first uint64
 for it.Next() {k:=it.Key();if len(k)==10 && k[9]=='n' {first=binary.BigEndian.Uint64(k[1:9]);break}}
 iterErr:=it.Error();it.Release();if iterErr!=nil {panic(iterErr)}
 report:=map[string]any{"schema":"omega.bor.db.audit.v1","readOnly":true,"checkedAt":time.Now().UTC().Format(time.RFC3339),
 "headNumber":headNumber,"headHash":headHash.Hex(),"headStateRoot":head.Root.Hex(),
 "firstRetainedCanonicalNonGenesis":first,"ancientOffset":rawdb.ReadOffsetOfCurrentAncientFreezer(db),
 "lastAncientOffset":rawdb.ReadOffsetOfLastAncientFreezer(db),"stateScheme":rawdb.ReadStateScheme(db),
 "persistentStateId":rawdb.ReadPersistentStateID(db),"headStateId":rawdb.ReadStateID(db,head.Root),
 "persistentRootNodeHash":crypto.Keccak256Hash(rawdb.ReadAccountTrieNode(db,nil)).Hex(),
 "persistentRootNodeBytes":len(rawdb.ReadAccountTrieNode(db,nil)),"snapshotRoot":rawdb.ReadSnapshotRoot(db).Hex(),
 "headBodyBytes":len(rawdb.ReadBodyRLP(db,headHash,headNumber)),
 "headReceiptsBytes":len(rawdb.ReadReceiptsRLP(db,headHash,headNumber)),
 "headDifficultyPresent":rawdb.ReadTd(db,headHash,headNumber)!=nil}
 var failures []string
 var prev common.Hash
 checked:=uint64(0)
 if first>0 && headNumber>=first && headNumber-first<=500000 {
  for n:=first;n<=headNumber;n++ {
   hash:=rawdb.ReadCanonicalHash(db,n)
   h:=rawdb.ReadHeaderFromKvStore(db,hash,n)
   if hash==(common.Hash{}) || h==nil || h.Hash()!=hash {failures=append(failures,fmt.Sprintf("HEADER_MISSING_OR_HASH_MISMATCH:%d",n));break}
   if n>first && h.ParentHash!=prev {failures=append(failures,fmt.Sprintf("PARENT_MISMATCH:%d",n));break}
   if n==first {report["firstHash"]=hash.Hex();report["firstParentHash"]=h.ParentHash.Hex()}
   if h.Root==rawdb.ReadSnapshotRoot(db) {report["snapshotRootBlock"]=n;report["snapshotRootBlockHash"]=hash.Hex()}
   prev=hash;checked++
  }
 } else {failures=append(failures,"RETAINED_RANGE_EXCEEDS_AUDIT_BOUND")}
 report["contiguousHeadersChecked"]=checked;report["failures"]=failures;report["durationMs"]=time.Since(started).Milliseconds()
 json.NewEncoder(os.Stdout).Encode(report)
}
