import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class SpatialSpectralCNN3D(nn.Module):
    """
    3D-Convolutional Neural Network feature extractor.
    Accepts 3D hyperspectral sub-volumes (Batch, Channels=1, Depth=Bands, Height=Patch, Width=Patch)
    and extracts inter-band spectral absorption features combined with local spatial foliar context.
    """
    def __init__(self, in_channels: int = 1, out_features: int = 128):
        super().__init__()
        # 3D Convolution layer 1
        self.conv1 = nn.Conv3d(in_channels, 16, kernel_size=(7, 3, 3), stride=(2, 1, 1), padding=(3, 1, 1))
        self.bn1 = nn.BatchNorm3d(16)
        
        # 3D Convolution layer 2
        self.conv2 = nn.Conv3d(16, 32, kernel_size=(5, 3, 3), stride=(2, 1, 1), padding=(2, 1, 1))
        self.bn2 = nn.BatchNorm3d(32)
        
        # 3D Convolution layer 3
        self.conv3 = nn.Conv3d(32, 64, kernel_size=(3, 3, 3), stride=(2, 1, 1), padding=(1, 1, 1))
        self.bn3 = nn.BatchNorm3d(64)
        
        self.adaptive_pool = nn.AdaptiveAvgPool3d((4, 2, 2))
        self.fc = nn.Linear(64 * 4 * 2 * 2, out_features)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Expected input shape: (B, 1, Bands, H, W)
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = self.adaptive_pool(x)
        x = x.view(x.size(0), -1)
        embeddings = self.fc(x)
        return embeddings

class SpectralTransformerEncoder(nn.Module):
    """
    Vision Transformer (ViT) encoder modeling long-range non-local spectral dependencies
    and inter-band interactions across the contiguous spectrum.
    """
    def __init__(self, d_model: int = 128, nhead: int = 4, num_layers: int = 3, dim_feedforward: int = 256):
        super().__init__()
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=0.1,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (B, Sequence_Length, d_model)
        b = x.size(0)
        cls_tokens = self.cls_token.expand(b, -1, -1)
        x = torch.cat((cls_tokens, x), dim=1)
        transformed = self.transformer_encoder(x)
        return transformed[:, 0, :]  # CLS token representation

class Hybrid3DCNN_ViT(nn.Module):
    """
    Master Hybrid 3D-CNN + Vision Transformer Architecture.
    Combines fine-grained spatial-spectral feature extraction (3D-CNN)
    with global sequence attention across spectral tokens (Vision Transformer).
    """
    def __init__(self, num_bands: int = 100, patch_size: int = 9, num_classes: int = 6, embed_dim: int = 128):
        super().__init__()
        self.num_bands = num_bands
        self.patch_size = patch_size
        self.num_classes = num_classes
        
        # Branch 1: 3D-CNN spatial-spectral extractor
        self.cnn3d = SpatialSpectralCNN3D(in_channels=1, out_features=embed_dim)
        
        # Branch 2: Spectral Patch Transformer Projection
        # Projects groups of spectral bands into sequence tokens
        self.num_spectral_tokens = 10
        self.bands_per_token = num_bands // self.num_spectral_tokens
        self.spectral_token_proj = nn.Linear(self.bands_per_token * patch_size * patch_size, embed_dim)
        self.pos_embedding = nn.Parameter(torch.randn(1, self.num_spectral_tokens, embed_dim))
        
        self.vit = SpectralTransformerEncoder(d_model=embed_dim, nhead=4, num_layers=3)
        
        # Fusion Classifier Head
        self.fusion_fc = nn.Sequential(
            nn.Linear(embed_dim * 2, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes)
        )

    def forward(self, patch: torch.Tensor) -> torch.Tensor:
        """
        Input: (B, Bands, Patch, Patch)
        """
        b, bands, h, w = patch.shape
        
        # 1. Forward 3D-CNN branch: reshape to (B, 1, Bands, H, W)
        x_3d = patch.unsqueeze(1)
        cnn_features = self.cnn3d(x_3d)  # (B, embed_dim)
        
        # 2. Forward ViT branch: chunk spectral bands into sequence of tokens
        # Crop bands to exact divisible multiple
        valid_bands = self.num_spectral_tokens * self.bands_per_token
        p_sub = patch[:, :valid_bands, :, :]
        # Shape: (B, num_spectral_tokens, bands_per_token, H, W)
        tokens = p_sub.view(b, self.num_spectral_tokens, self.bands_per_token * h * w)
        proj_tokens = self.spectral_token_proj(tokens) + self.pos_embedding
        vit_features = self.vit(proj_tokens)  # (B, embed_dim)
        
        # 3. Concatenate and classify
        fused = torch.cat((cnn_features, vit_features), dim=1)
        logits = self.fusion_fc(fused)
        return logits

