import { useEffect, useRef, useState } from "react";
import { Upload, FileText, Table as TableIcon, Plus, Eye, Trash2, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select as ShadSelect,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";

type ExtractionField = {
  id: string;
  name: string;
  type: "text" | "number" | "date" | "currency";
};

type TableType = {
  id: string;
  name: string;
  fields: ExtractionField[];
  configured: boolean;
};

type DataRow = {
  id: number;
  file: string;
  extractText: string;
  [key: string]: string | number;
};

const initialTables: TableType[] = [
  {
    id: "financial",
    name: "Financial Documents",
    configured: true,
    fields: [
      { id: "amount", name: "Amount", type: "currency" },
      { id: "iban", name: "IBAN", type: "text" },
      { id: "country", name: "Country", type: "text" },
      { id: "date", name: "Date", type: "date" },
    ],
  },
];

const financialDummyData: DataRow[] = [
  { id: 1, file: "file1234.dcm", extractText: "In a laoreet purus. Integer ipsum quam, lac...", amount: "$650.00", iban: "NL68RG8...", country: "The Netherlands", date: "2023-11-05" },
  { id: 2, file: "file1234.dcm", extractText: "Aliquam pulvinar vestibulum blandit. Donec...", amount: "$600.50", iban: "NL83RA5D...", country: "The Netherlands", date: "2023-11-07" },
  { id: 3, file: "file1234.dcm", extractText: "Aliquam porta nisl ex, congue pellentes...", amount: "$900.20", iban: "LU0301023...", country: "Luxembourg", date: "2023-11-10" },
  { id: 4, file: "file1234.dcm", extractText: "In a laoreet purus. Integer ipsum quam, lac...", amount: "$350.75", iban: "LU1801012...", country: "Luxembourg", date: "2023-11-12" },
  { id: 5, file: "file123a.dcm", extractText: "Aliquam pulvinar vestibulum blandit. Donec...", amount: "$900.30", iban: "PL0710902...", country: "Poland", date: "2023-11-15" },
  { id: 6, file: "file123a.dcm", extractText: "Vestibulum eu quam nec neque pellentesque...", amount: "$700.60", iban: "GB7791ABC...", country: "United Kingdom", date: "2023-11-18" },
  { id: 7, file: "file123a.dcm", extractText: "Vestibulum eu quam nec neque pellentesque...", amount: "$550.00", iban: "GB28BARC...", country: "United Kingdom", date: "2023-11-21" },
  { id: 8, file: "file123a.dcm", extractText: "Vestibulum eu quam nec neque pellentesque...", amount: "$1000.60", iban: "GB24BARC...", country: "United Kingdom", date: "2023-11-24" },
];

const MODEL_OPTIONS = [
  { label: "Claude 3.5 Sonnet", value: "anthropic.claude-3-5-sonnet-20240620-v1:0" },
  { label: "Amazon Nova Pro", value: "amazon.nova-pro-v1:0" },
];

function hashFields(fields: string[]): string {
  const str = JSON.stringify(fields.map(f => ({ name: f, type: "string" })));
  let hash = 0, i, chr;
  for (i = 0; i < str.length; i++) {
    chr = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + chr;
    hash |= 0;
  }
  return Math.abs(hash).toString();
}

type StatusState = { type: "error" | "polling" | "success"; message: string } | null;

export default function DataExtraction() {
  const [selectedRow, setSelectedRow] = useState<DataRow | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  const [tables, setTables] = useState<TableType[]>(initialTables);
  const [currentTable, setCurrentTable] = useState<string>(tables[0].id);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isConfigDrawerOpen, setIsConfigDrawerOpen] = useState(false);
  const [extractionFields, setExtractionFields] = useState<ExtractionField[]>([]);
//   const [isExtracting, setIsExtracting] = useState(false);
  const [isNewTableDialogOpen, setIsNewTableDialogOpen] = useState(false);
  const [newTableName, setNewTableName] = useState("");
  
  // Store data per table
  const [tableData, setTableData] = useState<Record<string, DataRow[]>>({
    financial: financialDummyData
  });

  const [model, setModel] = useState(MODEL_OPTIONS[0].value);
  const [status, setStatus] = useState<StatusState>(null);
  const [polling, setPolling] = useState(false);
  const [elapsed, setElapsed] = useState<number>(0);
  const [finalTime, setFinalTime] = useState<number | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const timerIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const submitTimeRef = useRef<number | null>(null);

//   const BASE_URL = "https://d2heck21lned7f.cloudfront.net";
const BASE_URL = "http://localhost:5000/api";

  const activeTable = tables.find(t => t.id === currentTable);
  const extractedData = tableData[currentTable] || [];

  const startTimer = () => {
    setElapsed(0);
    if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    timerIntervalRef.current = setInterval(() => setElapsed(prev => prev + 1), 1000);
  };
  
  const stopTimer = () => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearTimeout(pollIntervalRef.current);
      stopTimer();
    };
  }, []);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    
    if (file && activeTable && !activeTable.configured) {
      toast.error("Configuration Required", {
        description: "Please configure fields for this table before uploading files."
      });
      e.target.value = "";
      return;
    }
    
    setUploadedFile(file);
    setStatus(null);
    setFinalTime(null);
    setElapsed(0);
  };

  const handleRowClick = (row: DataRow) => {
    setSelectedRow(row);
    setExtractionFields(activeTable?.fields || []);
    setIsDrawerOpen(true);
  };

  const handleAddField = () => {
    const newField: ExtractionField = {
      id: `field_${Date.now()}`,
      name: "New Field",
      type: "text",
    };
    setExtractionFields((prev) => [...prev, newField]);
  };

  const handleRemoveField = (fieldId: string) => {
    setExtractionFields((prev) => prev.filter(f => f.id !== fieldId));
  };

  const handleFieldChange = (fieldId: string, key: keyof ExtractionField, value: string) => {
    setExtractionFields(prev => prev.map(f => (f.id === fieldId ? { ...f, [key]: value } : f)));
  };

  const getFieldsListForHash = () => {
    const names = activeTable?.fields.map(f => f.name) || [];
    return names.length ? names : ["value"];
  };

  // Helper function to map API response to table row based on field names
//   const mapApiResponseToRow = (apiFields: Record<string, any>): Record<string, any> => {
//     const mappedData: Record<string, any> = {};
    
//     if (!activeTable) return mappedData;
    
//     // Create a mapping from field names (used in API) to field IDs (used in table)
//     activeTable.fields.forEach(field => {
//       // Try to match field name (case-insensitive, with/without spaces/underscores)
//       const fieldNameNormalized = field.name.toLowerCase().replace(/[\s_-]+/g, '');
      
//       // Check all keys in the API response
//       for (const [apiKey, apiValue] of Object.entries(apiFields)) {
//         const apiKeyNormalized = apiKey.toLowerCase().replace(/[\s_-]+/g, '');
        
//         if (fieldNameNormalized === apiKeyNormalized) {
//           mappedData[field.id] = apiValue;
//           break;
//         }
//       }
//     });
    
//     return mappedData;
//   };

  const startPolling = () => {
    setPolling(true);
    pollForResult();
  };

  const stopPolling = () => {
    setPolling(false);
    if (pollIntervalRef.current) {
      clearTimeout(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    stopTimer();
  };

  const pollForResult = async () => {
    if (!uploadedFile) return;
    const fieldsHash = hashFields(getFieldsListForHash());
    try {
      const res = await fetch(`${BASE_URL}/extracted/input/${model}/${fieldsHash}/${uploadedFile.name}.json`);
      if (res.status === 200) {
        const data = await res.json();
        stopPolling();
        const timeTaken = Math.round((Date.now() - (submitTimeRef.current || Date.now())) / 1000);
        setFinalTime(timeTaken);
        setStatus({ type: "success", message: `Success! Completed in ${timeTaken} seconds.` });
        toast.success("Extraction Complete", { description: `Completed in ${timeTaken}s.` });

        // Populate extracted data into table
        const currentData = tableData[currentTable] || [];
        const newRow: DataRow = {
          id: currentData.length + 1,
          file: uploadedFile.name,
          extractText: "Extracted content...",
          ...(data.fields || data)
        };
        setTableData(prev => ({
          ...prev,
          [currentTable]: [...(prev[currentTable] || []), newRow]
        }));
        
      } else if (res.status === 403) {
        setStatus({ type: "polling", message: "Result not ready yet. Polling..." });
        pollIntervalRef.current = setTimeout(pollForResult, 2000);
      } else {
        setStatus({ type: "error", message: `Unexpected status: ${res.status}` });
        stopPolling();
      }
    } catch {
      setStatus({ type: "error", message: "Error polling for result." });
      stopPolling();
    }
  };

  const handleSubmitToCDN = async () => {
  if (!activeTable?.configured) {
    toast.error("Configuration Required");
    return;
  }
  
  if (!uploadedFile) {
    toast.error("Please select a file to submit.");
    return;
  }
  
  setStatus({ type: "polling", message: "Uploading and extracting..." });
  setFinalTime(null);
  setElapsed(0);
  submitTimeRef.current = Date.now();
  startTimer();
  
  try {
    const formData = new FormData();
    formData.append('file', uploadedFile);
    formData.append('table', JSON.stringify({
      id: currentTable,
      name: activeTable.name,
      fields: activeTable.fields
    }));
    formData.append('model', model);
    
    const response = await fetch(`${BASE_URL}/extract`, {
      method: 'POST',
      body: formData
    });
    
    if (response.ok) {
      const data = await response.json();
      stopTimer();
      const timeTaken = Math.round((Date.now() - (submitTimeRef.current || Date.now())) / 1000);
      setFinalTime(timeTaken);
      setStatus({ type: "success", message: `Success! Completed in ${timeTaken} seconds.` });
      
      // Populate table
      const currentData = tableData[currentTable] || [];
      const newRow: DataRow = {
        id: currentData.length + 1,
        file: uploadedFile.name,
        extractText: "Extracted content...",
        ...data.fields
      };
      setTableData(prev => ({
        ...prev,
        [currentTable]: [...(prev[currentTable] || []), newRow]
      }));
      
      toast.success("Extraction Complete", { description: `Completed in ${timeTaken}s.` });
    } else {
      const error = await response.json();
      setStatus({ type: "error", message: error.error || "Extraction failed" });
      stopTimer();
    }
  } catch (err) {
    console.error("Network error:", err);
    setStatus({ type: "error", message: "Network error" });
    stopTimer();
  }
};

//   const handleSubmitToCDN = async () => {
//     if (!activeTable?.configured) {
//       toast.error("Configuration Required", {
//         description: "Please configure fields for this table before submitting."
//       });
//       return;
//     }
    
//     if (!uploadedFile) {
//       toast.error("Please select a file to submit.");
//       return;
//     }
    
//     const fieldsHash = hashFields(getFieldsListForHash());
//     const inputUrl = `${BASE_URL}/input/${model}/${fieldsHash}/${uploadedFile.name}`;
//     const outputUrl = `${BASE_URL}/extracted/input/${model}/${fieldsHash}/${uploadedFile.name}.json`;

//     setStatus({ type: "polling", message: "Checking for existing input..." });
//     setFinalTime(null);
//     setElapsed(0);
//     submitTimeRef.current = Date.now();

//     try {
//       const checkRes = await fetch(inputUrl, { method: "GET" });
//       if (checkRes.status === 403) {
//         setStatus({ type: "polling", message: "Uploading and polling for result..." });
//         const headers: Record<string, string> = {
//           "x-amz-meta-model-id-override": model,
//           "x-amz-meta-fields-override": JSON.stringify(getFieldsListForHash().map(n => ({ name: n, type: "string" }))),
//         };
//         await fetch(inputUrl, { method: "PUT", body: uploadedFile, headers });
//         toast.success("Submitted!", { description: "Started extraction and polling for result." });
//         startPolling();
//         startTimer();
//       } else if ([200, 304].includes(checkRes.status)) {
//         setStatus({ type: "polling", message: "Input exists, fetching output..." });
//         startTimer();
//         const outputRes = await fetch(outputUrl, { method: "GET" });
//         if (outputRes.status === 200) {
//           const data = await outputRes.json();
//           stopTimer();
//           const timeTaken = Math.round((Date.now() - (submitTimeRef.current || Date.now())) / 1000);
//           setFinalTime(timeTaken);
//           setStatus({ type: "success", message: `Success! Completed in ${timeTaken} seconds.` });
          
//           // Populate extracted data into table
//           const currentData = tableData[currentTable] || [];
//           const newRow: DataRow = {
//             id: currentData.length + 1,
//             file: uploadedFile.name,
//             extractText: "Extracted content...",
//             ...(data.fields || data)
//           };
//           setTableData(prev => ({
//             ...prev,
//             [currentTable]: [...(prev[currentTable] || []), newRow]
//           }));
          
//           toast.success("Extraction Complete", { description: `Completed in ${timeTaken}s.` });
//         } else {
//           setStatus({ type: "polling", message: "Output not ready, polling..." });
//           startPolling();
//         }
//       } else {
//         setStatus({ type: "error", message: `Unexpected status on input check: ${checkRes.status}` });
//       }
//     } catch {
//       setStatus({ type: "error", message: "Error checking input existence." });
//     }
//   };

  const handlePollClick = () => {
    if (polling) {
      stopPolling();
      setStatus({ type: "error", message: "Polling stopped by user." });
    } else {
      if (!uploadedFile) {
        toast.error("Upload a file first.");
        return;
      }
      setStatus({ type: "polling", message: "Polling for result..." });
      setFinalTime(null);
      setElapsed(0);
      submitTimeRef.current = Date.now();
      startPolling();
      startTimer();
    }
  };

  const handleSaveConfiguration = () => {
    if (extractionFields.length === 0) {
      toast.error("No fields configured", {
        description: "Please add at least one field before saving."
      });
      return;
    }
    
    const updatedTables = tables.map(t =>
      t.id === currentTable ? { ...t, fields: extractionFields, configured: true } : t
    );
    setTables(updatedTables);
    toast("Configuration Saved",{
      description: "Field configuration updated successfully.",
    });
    setIsDrawerOpen(false);
    setIsConfigDrawerOpen(false);
  };

  const handleAddTable = () => {
    setNewTableName("");
    setIsNewTableDialogOpen(true);
  };

  const handleCreateTable = () => {
    if (!newTableName.trim()) {
      toast.error("Please enter a table name.");
      return;
    }
    const newTable: TableType = {
      id: `table_${Date.now()}`,
      name: newTableName.trim(),
      fields: [],
      configured: false,
    };
    setTables(prev => [...prev, newTable]);
    setCurrentTable(newTable.id);
    
    // Initialize empty data for new table
    setTableData(prev => ({
      ...prev,
      [newTable.id]: []
    }));
    
    setIsNewTableDialogOpen(false);
    setNewTableName("");
    
    // Open configuration drawer for new table
    setExtractionFields([]);
    setIsConfigDrawerOpen(true);
    
    toast("Table Created",{ 
      description: `"${newTable.name}" created. Please configure fields before uploading files.` 
    });
  };

  const handleConfigureTable = () => {
    setExtractionFields(activeTable?.fields || []);
    setIsConfigDrawerOpen(true);
  };

  const statusClasses =
    status?.type === "error"
      ? "bg-destructive text-destructive-foreground"
      : status?.type === "polling"
      ? "bg-amber-400 text-black"
      : status?.type === "success"
      ? "bg-emerald-500 text-white"
      : "bg-muted text-muted-foreground";

  return (
    <>
      <div className="flex h-[calc(100vh-8rem)] gap-4">
        <div className="flex-1 flex flex-col gap-4">
          <Card className="p-6 bg-card border-border">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="md:col-span-2">
                <Label htmlFor="file-upload" className="text-sm font-medium text-foreground mb-2 block">
                  Upload Data
                </Label>
                <div className="flex gap-2">
                  <Input
                    id="file-upload"
                    type="file"
                    accept=".pdf,.xlsx,.xls,.csv,.png"
                    onChange={handleFileUpload}
                    className="flex-1"
                    disabled={!activeTable?.configured}
                  />
                  <Button 
                    onClick={handleSubmitToCDN} 
                    className="bg-primary text-primary-foreground hover:bg-primary/90"
                    disabled={!activeTable?.configured || !uploadedFile}
                  >
                    <Upload className="w-4 h-4 mr-2" />
                    Submit
                  </Button>
                </div>
                {uploadedFile && (
                  <p className="text-sm text-muted-foreground mt-2">
                    Selected: {uploadedFile.name}
                  </p>
                )}
                {activeTable && !activeTable.configured && (
                  <p className="text-sm text-amber-600 mt-2 flex items-center gap-1">
                    <Settings className="w-4 h-4" />
                    Configure fields before uploading files
                  </p>
                )}
              </div>

              <div className="space-y-4">
                <div>
                  <Label className="text-sm font-medium text-foreground mb-2 block">
                    Table Type
                  </Label>
                  <div className="flex gap-2">
                    <ShadSelect value={currentTable} onValueChange={setCurrentTable}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select table" />
                      </SelectTrigger>
                      <SelectContent>
                        {tables.map(table => (
                          <SelectItem key={table.id} value={table.id}>
                            {table.name} {!table.configured && "⚠️"}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </ShadSelect>
                    <Button onClick={handleAddTable} variant="outline" size="icon">
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div>
                  <Label className="text-sm font-medium text-foreground mb-2 block">
                    Model
                  </Label>
                  <ShadSelect value={model} onValueChange={setModel}>
                    <SelectTrigger>
                      <SelectValue placeholder="Choose model" />
                    </SelectTrigger>
                    <SelectContent>
                      {MODEL_OPTIONS.map(opt => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </ShadSelect>
                </div>
              </div>
            </div>

            {status && (
              <div className={`mt-4 rounded-md px-4 py-2 text-sm font-medium shadow-sm ${statusClasses}`}>
                <div className="flex items-center justify-between">
                  <span>{status.message}</span>
                  <div className="text-xs font-normal">
                    {status.type === "polling" && <span>Elapsed: {elapsed}s</span>}
                    {status.type === "success" && finalTime !== null && <span>Total time: {finalTime}s</span>}
                  </div>
                </div>
              </div>
            )}
          </Card>

          <Card className="flex-1 overflow-hidden bg-card border-border">
            <div className="h-full overflow-auto">
              <Table>
                <TableHeader className="sticky top-0 bg-muted/50 backdrop-blur">
                  <TableRow className="border-border hover:bg-transparent">
                    <TableHead className="w-12 text-muted-foreground">#</TableHead>
                    <TableHead className="text-muted-foreground">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4" />
                        File
                      </div>
                    </TableHead>
                    <TableHead className="text-muted-foreground">Extract text</TableHead>
                    {activeTable?.fields.map(field => (
                      <TableHead key={field.id} className="text-muted-foreground">
                        {field.name}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {extractedData.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={3 + (activeTable?.fields.length || 0)} className="text-center text-muted-foreground py-8">
                        {activeTable?.configured 
                          ? "No data yet. Upload and extract files to see results here."
                          : "Configure fields for this table to start extracting data."}
                      </TableCell>
                    </TableRow>
                  ) : (
                    extractedData.map((row) => (
                      <TableRow
                        key={row.id}
                        onClick={() => handleRowClick(row)}
                        className={`cursor-pointer border-border ${
                          selectedRow?.id === row.id ? "bg-accent/50" : "hover:bg-accent/30"
                        }`}
                      >
                        <TableCell className="text-muted-foreground">{row.id}</TableCell>
                        <TableCell className="font-mono text-sm text-foreground">{row.file}</TableCell>
                        <TableCell className="text-muted-foreground max-w-md truncate">
                          {row.extractText}
                        </TableCell>
                        {activeTable?.fields.map(field => (
                          <TableCell key={field.id} className="text-foreground">
                            {row[field.id] || "-"}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </Card>
        </div>

        <div className="w-80 flex flex-col gap-4">
          <Card className="p-4 bg-card border-border">
            <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
              <TableIcon className="w-4 h-4" />
              Quick Actions
            </h3>
            <div className="space-y-2">
              <Button
                onClick={handleConfigureTable}
                variant="outline"
                className="w-full"
              >
                <Settings className="w-4 h-4 mr-2" />
                Configure Table
              </Button>
              <Button
                onClick={() => setIsDrawerOpen(true)}
                variant="outline"
                className="w-full"
                disabled={!activeTable?.configured}
              >
                <Eye className="w-4 h-4 mr-2" />
                View Configuration
              </Button>
              <div className="flex gap-2">
                <Button 
                  onClick={handlePollClick} 
                  variant="outline" 
                  className="flex-1"
                  disabled={!uploadedFile}
                >
                  {polling ? "Stop Polling" : "Poll for Result"}
                </Button>
              </div>
            </div>
          </Card>

          <Card className="p-4 bg-card border-border">
            <h3 className="font-semibold text-foreground mb-2">Active Fields</h3>
            {activeTable?.configured ? (
              <div className="space-y-2">
                {(activeTable?.fields || []).map(field => (
                  <div key={field.id} className="p-2 bg-muted/50 rounded-md text-sm">
                    <div className="font-medium text-foreground">{field.name}</div>
                    <div className="text-xs text-muted-foreground">{field.type}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground p-4 text-center border border-dashed rounded-md">
                No fields configured. Click "Configure Table" to add fields.
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Configuration Drawer */}
      <Drawer open={isConfigDrawerOpen} onOpenChange={setIsConfigDrawerOpen} direction="right">
        <DrawerContent className="fixed h-screen right-0 left-auto w-[600px] rounded-none border-none rounded-l-lg bg-card shadow-xl">
          <DrawerHeader className="border-b">
            <DrawerTitle>Configure Table: {activeTable?.name}</DrawerTitle>
            <DrawerDescription>
              Add and configure fields for data extraction. At least one field is required.
            </DrawerDescription>
          </DrawerHeader>

          <div className="p-6 overflow-y-auto flex-1 space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-medium text-foreground">Extraction Fields</h4>
              <Button onClick={handleAddField} size="sm" variant="outline">
                <Plus className="w-4 h-4 mr-1" />
                Add Field
              </Button>
            </div>

            {extractionFields.length === 0 && (
              <div className="text-center p-8 border border-dashed rounded-lg">
                <p className="text-muted-foreground mb-4">No fields configured yet</p>
                <Button onClick={handleAddField} variant="outline">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Your First Field
                </Button>
              </div>
            )}

            {extractionFields.map((field, index) => (
              <Card key={field.id} className="p-4 bg-card">
                <div className="flex items-start justify-between mb-3">
                  <div className="text-sm font-medium text-foreground">Field {index + 1}</div>
                  <Button onClick={() => handleRemoveField(field.id)} size="sm" variant="ghost">
                    <Trash2 className="w-4 h-4 text-destructive" />
                  </Button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs text-muted-foreground">Field Name</Label>
                    <Input
                      value={field.name}
                      onChange={(e) => handleFieldChange(field.id, "name", e.target.value)}
                      className="mt-1"
                      placeholder="e.g., Invoice Number, Total Amount"
                    />
                  </div>

                  <div>
                    <Label className="text-xs text-muted-foreground">Type</Label>
                    <ShadSelect
                      value={field.type}
                      onValueChange={(value) => handleFieldChange(field.id, "type", value)}
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="text">Text</SelectItem>
                        <SelectItem value="number">Number</SelectItem>
                        <SelectItem value="date">Date</SelectItem>
                        <SelectItem value="currency">Currency</SelectItem>
                      </SelectContent>
                    </ShadSelect>
                  </div>
                </div>
              </Card>
            ))}
          </div>

          <DrawerFooter className="flex-row gap-2 border-t">
            <DrawerClose asChild>
              <Button variant="outline" className="flex-1">Cancel</Button>
            </DrawerClose>
            <Button 
              onClick={handleSaveConfiguration} 
              className="flex-1"
              disabled={extractionFields.length === 0}
            >
              Save Configuration
            </Button>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>

      {/* View Configuration Drawer */}
      <Drawer open={isDrawerOpen} onOpenChange={setIsDrawerOpen} direction="right">
        <DrawerContent className="fixed h-screen right-0 left-auto w-[600px] rounded-none border-none rounded-l-lg bg-card shadow-xl">
          <DrawerHeader className="border-b">
            <DrawerTitle>Field Configuration</DrawerTitle>
            <DrawerDescription>
              {selectedRow ? `Viewing extraction for ${selectedRow.file}` : "View extraction fields"}
            </DrawerDescription>
          </DrawerHeader>

          <div className="p-6 overflow-y-auto flex-1 space-y-4">
            {selectedRow && (
              <Card className="p-4 bg-muted/20">
                <h4 className="font-medium text-sm mb-2 text-foreground">Source Data Preview</h4>
                <div className="text-xs text-muted-foreground space-y-1">
                  <div><span className="font-medium">File:</span> {selectedRow.file}</div>
                  <div><span className="font-medium">Extract Text:</span> {selectedRow.extractText}</div>
                </div>
              </Card>
            )}

            <div className="space-y-3">
              <h4 className="font-medium text-foreground">Extracted Fields</h4>
              {activeTable?.fields.map(field => (
                <Card key={field.id} className="p-4 bg-card">
                  <div className="grid grid-cols-1 gap-3">
                    <div>
                      <Label className="text-xs text-muted-foreground">Field Name</Label>
                      <div className="mt-1 text-sm font-medium text-foreground">{field.name}</div>
                    </div>

                    <div>
                      <Label className="text-xs text-muted-foreground">Type</Label>
                      <div className="mt-1 text-sm text-foreground capitalize">{field.type}</div>
                    </div>

                    {selectedRow && (
                      <div className="p-3 bg-muted/30 rounded text-sm">
                        <div className="font-medium text-foreground mb-1">Extracted Value:</div>
                        <div className="text-foreground">
                          {selectedRow[field.id] || "-"}
                        </div>
                      </div>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          </div>

          <DrawerFooter className="flex-row gap-2 border-t">
            <DrawerClose asChild>
              <Button variant="outline" className="flex-1">Close</Button>
            </DrawerClose>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>

      {/* New Table Dialog */}
      <Dialog open={isNewTableDialogOpen} onOpenChange={setIsNewTableDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Table</DialogTitle>
            <DialogDescription>
              Enter a name for your new extraction table. You'll configure fields after creation.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <Label htmlFor="table-name" className="text-sm font-medium text-foreground">
              Table Name
            </Label>
            <Input
              id="table-name"
              value={newTableName}
              onChange={(e) => setNewTableName(e.target.value)}
              placeholder="e.g., Invoices, Receipts, Contracts"
              className="mt-2"
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCreateTable();
              }}
            />
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsNewTableDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateTable}>Create Table</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}