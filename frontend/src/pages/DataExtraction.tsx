/* eslint-disable @typescript-eslint/no-explicit-any */
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
    document_table_id?: number; // DB ID
};

type DataRow = {
    id: number;
    file: string;
    extractText: string;
    [key: string]: string | number;
};

const MODEL_OPTIONS = [
    { label: "Llama 3.1 8B", value: "llama-3.1-8b-instant" },
    { label: "Mixtral 8x7B", value: "mixtral-8x7b-32768" },
];

type StatusState = { type: "error" | "polling" | "success"; message: string } | null;

export default function DataExtraction() {
    const [selectedRow, setSelectedRow] = useState<DataRow | null>(null);
    const [uploadedFile, setUploadedFile] = useState<File | null>(null);

    const [tables, setTables] = useState<TableType[]>([]);
    const [currentTable, setCurrentTable] = useState<string>("");
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isConfigDrawerOpen, setIsConfigDrawerOpen] = useState(false);
    const [extractionFields, setExtractionFields] = useState<ExtractionField[]>([]);
    const [isNewTableDialogOpen, setIsNewTableDialogOpen] = useState(false);
    const [newTableName, setNewTableName] = useState("");
    const [loading, setLoading] = useState(false);

    // Store data per table
    const [tableData, setTableData] = useState<Record<string, DataRow[]>>({});

    const [model, setModel] = useState(MODEL_OPTIONS[0].value);
    const [status, setStatus] = useState<StatusState>(null);
    const [elapsed, setElapsed] = useState<number>(0);
    const [finalTime, setFinalTime] = useState<number | null>(null);
    const timerIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const submitTimeRef = useRef<number | null>(null);

    const BASE_URL = "http://localhost:5000/api";

    const activeTable = tables.find(t => t.id === currentTable);
    const extractedData = tableData[currentTable] || [];

    // Fetch tables on mount
    useEffect(() => {
        fetchTables();
    }, []);

    // Fetch results when table changes
    useEffect(() => {
        if (currentTable) {
            fetchResults(currentTable);
        }
    }, [currentTable]);

    const fetchTables = async () => {
        try {
            const response = await fetch(`${BASE_URL}/tables`);
            if (!response.ok) throw new Error("Failed to fetch tables");

            const data = await response.json();
            const formattedTables: TableType[] = data.map((table: any) => ({
                id: table.table_id,
                name: table.name,
                document_table_id: table.id,
                configured: table.is_configured,
                fields: table.fields.map((field: any) => ({
                    id: field.field_id,
                    name: field.name,
                    type: field.field_type
                }))
            }));

            setTables(formattedTables);
            if (formattedTables.length > 0 && !currentTable) {
                setCurrentTable(formattedTables[0].id);
            }
        } catch (error) {
            console.error("Error fetching tables:", error);
            toast.error("Failed to load tables");
        }
    };

    const fetchResults = async (tableId: string) => {
        try {
            const response = await fetch(`${BASE_URL}/results?table_id=${tableId}&limit=100`);
            if (!response.ok) throw new Error("Failed to fetch results");

            const data = await response.json();
            const formattedData: DataRow[] = data.map((result: any) => ({
                id: result.id,
                file: result.filename,
                extractText: result.extracted_text || "Extracted content...",
                ...result.fields_mapped
            }));

            setTableData(prev => ({
                ...prev,
                [tableId]: formattedData
            }));
        } catch (error) {
            console.error("Error fetching results:", error);
        }
    };

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

    const handleSubmitExtraction = async () => {
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
        setLoading(true);

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
                console.log("Extraction response:", data);
                stopTimer();
                const timeTaken = Math.round((Date.now() - (submitTimeRef.current || Date.now())) / 1000);
                setFinalTime(timeTaken);
                setStatus({ type: "success", message: `Success! Completed in ${timeTaken} seconds.` });

                // Refresh results
                await fetchResults(currentTable);

                toast.success("Extraction Complete", { description: `Completed in ${timeTaken}s.` });
                setUploadedFile(null);

                // Reset file input
                const fileInput = document.getElementById('file-upload') as HTMLInputElement;
                if (fileInput) fileInput.value = '';
            } else {
                const error = await response.json();
                setStatus({ type: "error", message: error.error || "Extraction failed" });
                stopTimer();
                toast.error("Extraction failed", { description: error.error });
            }
        } catch (err) {
            console.error("Network error:", err);
            setStatus({ type: "error", message: "Network error" });
            stopTimer();
            toast.error("Network error", { description: "Failed to connect to server" });
        } finally {
            setLoading(false);
        }
    };

    const handleSaveConfiguration = async () => {
        if (extractionFields.length === 0) {
            toast.error("No fields configured", {
                description: "Please add at least one field before saving."
            });
            return;
        }

        try {
            const payload = {
                table_id: currentTable,
                name: activeTable?.name,
                fields: extractionFields.map(f => ({
                    field_id: f.id,
                    name: f.name,
                    field_type: f.type
                }))
            };

            const response = await fetch(`${BASE_URL}/tables`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error("Failed to save configuration");

            toast.success("Configuration Saved", {
                description: "Field configuration updated successfully.",
            });

            // Refresh tables
            await fetchTables();

            setIsDrawerOpen(false);
            setIsConfigDrawerOpen(false);
        } catch (error) {
            console.error("Error saving configuration:", error);
            toast.error("Failed to save configuration");
        }
    };

    const handleAddTable = () => {
        setNewTableName("");
        setIsNewTableDialogOpen(true);
    };

    const handleCreateTable = async () => {
        if (!newTableName.trim()) {
            toast.error("Please enter a table name.");
            return;
        }

        try {
            const payload = {
                table_id: `table_${Date.now()}`,
                name: newTableName.trim(),
                fields: []
            };

            const response = await fetch(`${BASE_URL}/tables`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error("Failed to create table");

            const newTable = await response.json();

            setIsNewTableDialogOpen(false);
            setNewTableName("");

            // Refresh tables
            await fetchTables();
            setCurrentTable(payload.table_id);

            // Open configuration drawer for new table
            setExtractionFields([]);
            setIsConfigDrawerOpen(true);

            toast.success("Table Created", {
                description: `"${newTable.name}" created. Please configure fields before uploading files.`
            });
        } catch (error) {
            console.error("Error creating table:", error);
            toast.error("Failed to create table");
        }
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
                                        accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp,.webp"
                                        onChange={handleFileUpload}
                                        className="flex-1"
                                        disabled={!activeTable?.configured || loading}
                                    />
                                    <Button
                                        onClick={handleSubmitExtraction}
                                        className="bg-primary text-primary-foreground hover:bg-primary/90"
                                        disabled={!activeTable?.configured || !uploadedFile || loading}
                                    >
                                        <Upload className="w-4 h-4 mr-2" />
                                        {loading ? "Processing..." : "Extract"}
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
                                                className={`cursor-pointer border-border ${selectedRow?.id === row.id ? "bg-accent/50" : "hover:bg-accent/30"
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