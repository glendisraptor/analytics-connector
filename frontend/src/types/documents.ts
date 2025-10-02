// Document Table Types
export interface DocumentTable {
    id: number;
    table_id: string;
    name: string;
    description?: string;
    is_configured: boolean;
    is_active: boolean;
    fields: DocumentField[];
    created_at: string;
}

export interface DocumentField {
    id: number;
    field_id: string;
    name: string;
    field_type: 'text' | 'currency' | 'date' | 'number' | 'email';
    is_required: boolean;
    display_order: number;
}

export interface CreateDocumentTableRequest {
    table_id: string;
    name: string;
    description?: string;
    fields: {
        field_id: string;
        name: string;
        field_type: string;
        is_required?: boolean;
    }[];
}

// Document Result Types
export interface DocumentResult {
    id: number;
    filename: string;
    stored_path?: string;
    document_table_id?: number;
    table_id: string;
    table_name: string;
    fields_mapped: Record<string, any>;
    fields_by_name: Record<string, any>;
    extracted_text?: string;
    model_id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    processing_time_ms?: number;
    created_at: string;
}

export interface ExtractDocumentRequest {
    file: File;
    table: {
        id: string;
        name: string;
        fields: DocumentField[];
    };
    model?: string;
}

export interface ExtractDocumentResponse {
    id: number;
    fields: Record<string, any>;
    source: {
        path: string;
        filename: string;
    };
    model_id: string;
    table_id: string;
    table_name: string;
    processing_time_ms: number;
    timestamp: string;
}

export interface ReExtractRequest {
    fields: {
        field_id: string;
        name: string;
        field_type: string;
    }[];
}

export interface ReExtractResponse {
    id: number;
    fields: Record<string, any>;
    processing_time_ms: number;
    message: string;
}